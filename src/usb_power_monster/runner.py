from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from .integrity import IntegrityError, mutate_and_verify, prepare_payload, verify_payload
from .model import IterationResult, RunConfig
from .platform_base import PlatformBackend


class MonsterRunner:
    def __init__(self, backend: PlatformBackend, config: RunConfig):
        self.backend = backend
        self.cfg = config
        self.run_dir = config.log_dir / time.strftime("%Y%m%d-%H%M%S")
        self.payload = config.target / ".usb-power-monster" / "payload.bin"
        self.results_path = self.run_dir / "iterations.jsonl"
        self.summary_path = self.run_dir / "summary.json"

    def _append(self, result: IterationResult) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with self.results_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), default=str, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def run(self) -> dict[str, object]:
        if not self.cfg.target.is_dir():
            raise NotADirectoryError(self.cfg.target)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        expected = prepare_payload(self.payload, self.cfg.payload_bytes, self.cfg.seed, self.cfg.fsync)
        successes = failures = 0
        started = time.time()
        self.backend.start_trace(self.run_dir)
        try:
            for iteration in range(1, self.cfg.cycles + 1):
                for state in self.cfg.states:
                    result = IterationResult(iteration=iteration, state=state, ok=False)
                    try:
                        # Pre-transition verification catches latent corruption from the prior cycle.
                        expected, io_ms, read_bytes = verify_payload(self.payload, expected)
                        result.io_latency_ms = io_ms
                        result.bytes_read += read_bytes

                        self.backend.configure_state(state)
                        if self.cfg.idle_ms:
                            time.sleep(self.cfg.idle_ms / 1000.0)
                        result.samples.extend(self.backend.wait_for_low_power(state))

                        wake_t0 = time.perf_counter_ns()
                        result.samples.extend(self.backend.wake(self.payload))
                        result.wake_latency_ms = (time.perf_counter_ns() - wake_t0) / 1e6

                        # Write-after-resume then full-file SHA-256 verification.
                        expected, written = mutate_and_verify(self.payload, iteration ^ hash(state), self.cfg.fsync)
                        result.bytes_written += written
                        digest, io_ms, read_bytes = verify_payload(self.payload, expected)
                        result.digest = digest
                        result.io_latency_ms = (result.io_latency_ms or 0.0) + io_ms
                        result.bytes_read += read_bytes
                        result.ok = True
                        successes += 1
                    except (OSError, RuntimeError, TimeoutError, IntegrityError, ValueError) as exc:
                        failures += 1
                        result.error = f"{type(exc).__name__}: {exc}"
                        context = self.backend.collect_failure_context()
                        if context:
                            failure_file = self.run_dir / f"failure-{iteration:06d}-{state}.log"
                            failure_file.write_text(context, encoding="utf-8", errors="replace")
                    finally:
                        self._append(result)
                    if not result.ok and self.cfg.fail_fast:
                        raise RuntimeError(result.error)
        finally:
            self.backend.stop_trace()

        summary: dict[str, object] = {
            "started_epoch": started,
            "duration_s": time.time() - started,
            "target": str(self.cfg.target),
            "payload": str(self.payload),
            "cycles": self.cfg.cycles,
            "states": [s.value for s in self.cfg.states],
            "attempts": successes + failures,
            "successes": successes,
            "failures": failures,
            "backend": self.backend.describe(),
            "results": str(self.results_path),
        }
        self.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
