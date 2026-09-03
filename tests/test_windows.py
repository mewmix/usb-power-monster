from __future__ import annotations

import subprocess
from pathlib import Path

from usb_power_monster.windows import WindowsBackend


def test_start_trace_adds_usb_providers_separately(tmp_path: Path) -> None:
    backend = WindowsBackend(Path(r"C:\Tools\UsbLPM.exe"))
    calls: list[tuple[tuple[str, ...], bool]] = []

    def fake_run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        calls.append((args, check))
        return subprocess.CompletedProcess(args, 0, "", "")

    backend._run = fake_run  # type: ignore[method-assign]
    backend.start_trace(tmp_path)

    etl = tmp_path / "usb.etl"
    assert calls == [
        (("logman", "stop", "-n", "USBPowerMonster"), False),
        (("logman", "delete", "-n", "USBPowerMonster"), False),
        ((
            "logman", "create", "trace", "-n", "USBPowerMonster",
            "-o", str(etl), "-nb", "128", "640", "-bs", "128", "-y",
        ), True),
        ((
            "logman", "update", "trace", "-n", "USBPowerMonster",
            "-p", "Microsoft-Windows-USB-USBXHCI", "(Rundown,Power)",
        ), True),
        ((
            "logman", "update", "trace", "-n", "USBPowerMonster",
            "-p", "Microsoft-Windows-USB-UCX", "(Rundown,Power)",
        ), True),
        ((
            "logman", "update", "trace", "-n", "USBPowerMonster",
            "-p", "Microsoft-Windows-USB-USBHUB3", "(Rundown,Power)",
        ), True),
        (("logman", "start", "-n", "USBPowerMonster"), True),
    ]


def test_stop_trace_stops_and_deletes_collector() -> None:
    backend = WindowsBackend(Path(r"C:\Tools\UsbLPM.exe"))
    calls: list[tuple[tuple[str, ...], bool]] = []

    def fake_run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        calls.append((args, check))
        return subprocess.CompletedProcess(args, 0, "", "")

    backend._run = fake_run  # type: ignore[method-assign]
    backend.stop_trace()

    assert calls == [
        (("logman", "stop", "-n", "USBPowerMonster"), False),
        (("logman", "delete", "-n", "USBPowerMonster"), False),
    ]
