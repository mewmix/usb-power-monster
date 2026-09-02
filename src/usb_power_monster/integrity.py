from __future__ import annotations

import hashlib
import os
import random
import time
from pathlib import Path


class IntegrityError(RuntimeError):
    pass


def _pattern(size: int, seed: int) -> bytes:
    rng = random.Random(seed)
    block = bytearray(min(size, 1024 * 1024))
    for i in range(len(block)):
        block[i] = rng.randrange(256)
    if size <= len(block):
        return bytes(block[:size])
    repeats, tail = divmod(size, len(block))
    return bytes(block) * repeats + bytes(block[:tail])


def prepare_payload(path: Path, size: int, seed: int, fsync: bool = True) -> str:
    payload = _pattern(size, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb", buffering=0) as f:
        f.write(payload)
        if fsync:
            os.fsync(f.fileno())
    return hashlib.sha256(payload).hexdigest()


def verify_payload(path: Path, expected: str, chunk_size: int = 1024 * 1024) -> tuple[str, float, int]:
    h = hashlib.sha256()
    total = 0
    t0 = time.perf_counter_ns()
    with path.open("rb", buffering=0) as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
            total += len(chunk)
    elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
    actual = h.hexdigest()
    if actual != expected:
        raise IntegrityError(f"SHA-256 mismatch expected={expected} actual={actual}")
    return actual, elapsed_ms, total


def mutate_and_verify(path: Path, iteration: int, fsync: bool = True) -> tuple[str, int]:
    if path.stat().st_size < 4096:
        raise ValueError("payload must be at least 4096 bytes")
    offset = (iteration * 4096) % (path.stat().st_size - 4096 + 1)
    block = _pattern(4096, iteration ^ 0x5A17)
    with path.open("r+b", buffering=0) as f:
        f.seek(offset)
        f.write(block)
        if fsync:
            os.fsync(f.fileno())
    h = hashlib.sha256()
    with path.open("rb", buffering=0) as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest(), len(block)
