from __future__ import annotations

import abc
from pathlib import Path

from .model import PowerState, StateSample


class PlatformBackend(abc.ABC):
    @abc.abstractmethod
    def describe(self) -> dict[str, str]: ...

    @abc.abstractmethod
    def configure_state(self, state: PowerState) -> None: ...

    @abc.abstractmethod
    def wait_for_low_power(self, state: PowerState, timeout_s: float = 5.0) -> list[StateSample]: ...

    @abc.abstractmethod
    def wake(self, target_file: Path) -> list[StateSample]: ...

    def start_trace(self, log_dir: Path) -> None:
        return None

    def stop_trace(self) -> None:
        return None

    def collect_failure_context(self) -> str:
        return ""
