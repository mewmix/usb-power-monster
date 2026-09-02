from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from .model import Evidence, PowerState, StateSample
from .platform_base import PlatformBackend


class WindowsBackend(PlatformBackend):
    def __init__(self, usblpm: Path | None = None):
        self.usblpm = usblpm or (Path(shutil.which("usblpm")) if shutil.which("usblpm") else None)
        self.trace_name = "USBPowerMonster"

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        cp = subprocess.run(args, text=True, capture_output=True, check=False)
        if check and cp.returncode:
            raise RuntimeError(f"command failed ({cp.returncode}): {' '.join(args)}\n{cp.stdout}\n{cp.stderr}")
        return cp

    def _usblpm(self, *args: str) -> None:
        if not self.usblpm:
            raise RuntimeError("USBLPM executable not found; provide --usblpm PATH for explicit U1/U2 control")
        self._run(str(self.usblpm), *args)

    def describe(self) -> dict[str, str]:
        return {
            "usblpm": str(self.usblpm) if self.usblpm else "unavailable",
            "selective_suspend": "Windows power policy / device driver controlled",
            "state_evidence": "requested unless ETW/analyzer confirms transition",
        }

    def configure_state(self, state: PowerState) -> None:
        if state == PowerState.U0:
            if self.usblpm:
                self._usblpm("/disable", "U1")
                self._usblpm("/disable", "U2")
        elif state == PowerState.U1:
            self._usblpm("/enable", "U1")
            self._usblpm("/disable", "U2")
        elif state == PowerState.U2:
            self._usblpm("/disable", "U1")
            self._usblpm("/enable", "U2")
        elif state == PowerState.U3:
            # U3 is reached through device/runtime selective suspend. Enabling the
            # global USB selective-suspend policy does not itself prove U3 entry.
            self._run("powercfg", "/SETACVALUEINDEX", "SCHEME_CURRENT", "SUB_USB", "USBSELECTIVE", "1")
            self._run("powercfg", "/SETACTIVE", "SCHEME_CURRENT")
        elif state == PowerState.SUSPEND:
            self._run("powercfg", "/SETACVALUEINDEX", "SCHEME_CURRENT", "SUB_USB", "USBSELECTIVE", "1")
            self._run("powercfg", "/SETACTIVE", "SCHEME_CURRENT")
        elif state == PowerState.L1:
            raise RuntimeError("USB2 L1 forcing is host-controller/tool specific on Windows; use Linux for deterministic L1 control")
        else:
            raise ValueError(f"unsupported Windows state: {state}")

    def wait_for_low_power(self, state: PowerState, timeout_s: float = 5.0) -> list[StateSample]:
        # Windows user mode does not provide a trustworthy generic per-device API
        # that says 'the physical link is now U1/U2/U3'. ETW/analyzer correlation
        # is therefore kept separate from requested state.
        time.sleep(min(timeout_s, 0.25))
        return [StateSample(time.monotonic_ns(), state, None, Evidence.REQUESTED,
            "state requested/configured; inspect ETW/analyzer trace for physical-state proof")]

    def wake(self, target_file: Path) -> list[StateSample]:
        with target_file.open("rb", buffering=0) as f:
            f.read(4096)
        return [StateSample(time.monotonic_ns(), PowerState.U0, None, Evidence.INFERRED,
            "successful file I/O implies device responsiveness; not physical U0 proof")]

    def start_trace(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        etl = log_dir / "usb.etl"
        self._run("logman", "stop", self.trace_name, "-ets", check=False)
        self._run("logman", "create", "trace", self.trace_name,
                  "-o", str(etl), "-p", "Microsoft-Windows-USB-USBXHCI", "0xffffffffffffffff", "0xff",
                  "-p", "Microsoft-Windows-USB-UCX", "0xffffffffffffffff", "0xff",
                  "-p", "Microsoft-Windows-USB-USBHUB3", "0xffffffffffffffff", "0xff", "-ets")

    def stop_trace(self) -> None:
        self._run("logman", "stop", self.trace_name, "-ets", check=False)

    def collect_failure_context(self) -> str:
        cp = self._run("wevtutil", "qe", "System", "/q:*[System[Provider[@Name='Microsoft-Windows-USB-USBHUB3']]]",
                       "/f:text", "/c:50", check=False)
        return (cp.stdout or cp.stderr)[-20000:]
