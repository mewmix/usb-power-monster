from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

from .linux import LinuxBackend
from .model import PowerState, RunConfig
from .runner import MonsterRunner
from .windows import WindowsBackend


def _states(value: str) -> tuple[PowerState, ...]:
    try:
        return tuple(PowerState(v.strip().upper()) for v in value.split(",") if v.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="usb-power-monster", description="USB storage power-state torture harness")
    p.add_argument("target", type=Path, help="mounted DUT directory; test data stays under .usb-power-monster")
    p.add_argument("--cycles", type=int, default=1000)
    p.add_argument("--payload-mib", type=int, default=16)
    p.add_argument("--idle-ms", type=int, default=250)
    p.add_argument("--states", type=_states, default=None, help="comma-separated U0,U1,U2,U3,L1,SUSPEND")
    p.add_argument("--log-dir", type=Path, default=Path("usb-power-monster-logs"))
    p.add_argument("--fail-fast", action="store_true")
    p.add_argument("--no-fsync", action="store_true")
    p.add_argument("--sysfs-device", type=Path, help="Linux USB sysfs device, e.g. /sys/bus/usb/devices/2-3")
    p.add_argument("--usblpm", type=Path, help="Windows USBLPM.exe path for explicit U1/U2 enablement")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.cycles < 1 or args.payload_mib < 1 or args.idle_ms < 0:
        raise SystemExit("cycles/payload must be positive; idle-ms cannot be negative")

    system = platform.system()
    if system == "Linux":
        if os.geteuid() != 0:
            raise SystemExit("Linux power controls require root; run with sudo")
        if not args.sysfs_device:
            raise SystemExit("Linux requires --sysfs-device /sys/bus/usb/devices/<bus-port>")
        backend = LinuxBackend(args.sysfs_device)
        default_states = (PowerState.U1, PowerState.U2, PowerState.U3)
    elif system == "Windows":
        backend = WindowsBackend(args.usblpm)
        default_states = (PowerState.U1, PowerState.U2, PowerState.U3)
    else:
        raise SystemExit(f"unsupported platform: {system}")

    cfg = RunConfig(
        target=args.target.resolve(), cycles=args.cycles, payload_mib=args.payload_mib,
        idle_ms=args.idle_ms, states=args.states or default_states, fsync=not args.no_fsync,
        fail_fast=args.fail_fast, log_dir=args.log_dir.resolve(), windows_usblpm=args.usblpm,
    )
    summary = MonsterRunner(backend, cfg).run()
    print(json.dumps(summary, indent=2))
    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
