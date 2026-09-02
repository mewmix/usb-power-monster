from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class PowerState(StrEnum):
    U0 = "U0"
    U1 = "U1"
    U2 = "U2"
    U3 = "U3"
    L0 = "L0"
    L1 = "L1"
    SUSPEND = "SUSPEND"


class Evidence(StrEnum):
    OBSERVED = "observed"
    HOST_REPORTED = "host-reported"
    REQUESTED = "requested"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class StateSample:
    monotonic_ns: int
    requested: PowerState | None
    reported: PowerState | None
    evidence: Evidence
    detail: str = ""


@dataclass(slots=True)
class IterationResult:
    iteration: int
    state: PowerState
    ok: bool
    wake_latency_ms: float | None = None
    io_latency_ms: float | None = None
    bytes_written: int = 0
    bytes_read: int = 0
    digest: str | None = None
    error: str | None = None
    samples: list[StateSample] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunConfig:
    target: Path
    cycles: int = 1000
    payload_mib: int = 16
    idle_ms: int = 250
    states: tuple[PowerState, ...] = (PowerState.U1, PowerState.U2, PowerState.U3)
    fsync: bool = True
    seed: int = 0xC0FFEE
    fail_fast: bool = False
    log_dir: Path = Path("usb-power-monster-logs")
    windows_usblpm: Path | None = None

    @property
    def payload_bytes(self) -> int:
        return self.payload_mib * 1024 * 1024
