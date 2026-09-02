from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .model import Evidence, PowerState, StateSample
from .platform_base import PlatformBackend


class LinuxBackend(PlatformBackend):
    def __init__(self, sysfs_device: Path):
        self.dev = sysfs_device
        self.power = self.dev / "power"
        if not self.power.exists():
            raise FileNotFoundError(f"USB sysfs power directory not found: {self.power}")

    def _write(self, name: str, value: str) -> None:
        p = self.power / name
        if not p.exists():
            raise RuntimeError(f"kernel does not expose {p}")
        p.write_text(value)

    def _read(self, name: str) -> str:
        p = self.power / name
        return p.read_text().strip() if p.exists() else "unavailable"

    def describe(self) -> dict[str, str]:
        return {
            "sysfs_device": str(self.dev),
            "runtime_status": self._read("runtime_status"),
            "u1": self._read("usb3_hardware_lpm_u1"),
            "u2": self._read("usb3_hardware_lpm_u2"),
            "usb2_lpm": self._read("usb2_hardware_lpm"),
        }

    def configure_state(self, state: PowerState) -> None:
        if state == PowerState.U0:
            self._write("control", "on")
        elif state == PowerState.U1:
            self._write("control", "on")
            self._write("usb3_hardware_lpm_u1", "enable")
            if (self.power / "usb3_hardware_lpm_u2").exists():
                self._write("usb3_hardware_lpm_u2", "disable")
        elif state == PowerState.U2:
            self._write("control", "on")
            if (self.power / "usb3_hardware_lpm_u1").exists():
                self._write("usb3_hardware_lpm_u1", "disable")
            self._write("usb3_hardware_lpm_u2", "enable")
        elif state == PowerState.U3:
            self._write("autosuspend_delay_ms", "0")
            self._write("control", "auto")
        elif state == PowerState.L1:
            self._write("control", "on")
            self._write("usb2_hardware_lpm", "1")
        elif state == PowerState.SUSPEND:
            self._write("autosuspend_delay_ms", "0")
            self._write("control", "auto")
        else:
            raise ValueError(f"unsupported Linux state: {state}")

    def wait_for_low_power(self, state: PowerState, timeout_s: float = 5.0) -> list[StateSample]:
        samples: list[StateSample] = []
        deadline = time.monotonic() + timeout_s
        if state in (PowerState.U3, PowerState.SUSPEND):
            while time.monotonic() < deadline:
                status = self._read("runtime_status")
                samples.append(StateSample(time.monotonic_ns(), state, state if status == "suspended" else None,
                    Evidence.HOST_REPORTED if status == "suspended" else Evidence.REQUESTED, status))
                if status == "suspended":
                    return samples
                time.sleep(0.02)
            raise TimeoutError(f"runtime suspend not reached; status={self._read('runtime_status')}")

        # Linux sysfs controls U1/U2/L1 enablement but does not prove every physical entry.
        samples.append(StateSample(time.monotonic_ns(), state, None, Evidence.REQUESTED,
            "LPM enabled; physical entry requires xHCI trace/analyzer evidence"))
        return samples

    def wake(self, target_file: Path) -> list[StateSample]:
        with target_file.open("rb", buffering=0) as f:
            f.read(4096)
        status = self._read("runtime_status")
        return [StateSample(time.monotonic_ns(), PowerState.U0, PowerState.U0 if status == "active" else None,
            Evidence.HOST_REPORTED if status == "active" else Evidence.INFERRED, status)]

    def collect_failure_context(self) -> str:
        cp = subprocess.run(["dmesg", "--ctime", "--level=err,warn"], text=True, capture_output=True, check=False)
        return cp.stdout[-20000:] if cp.stdout else cp.stderr[-5000:]
