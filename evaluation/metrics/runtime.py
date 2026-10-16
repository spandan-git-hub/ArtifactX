"""Runtime duration and peak memory measurement (spec C1.2).

Measures:
- Per-stage elapsed time in milliseconds
- Peak heap memory allocation via tracemalloc in MiB
- System environment metadata (CPU, OS, Python version, SQLite version)
"""

from __future__ import annotations

import os
import platform
import sqlite3
import sys
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Generator, Optional


@dataclass
class StageProfile:
    stage_name: str
    duration_ms: float
    peak_memory_mib: float


@dataclass
class EnvironmentInfo:
    os: str
    os_release: str
    python_version: str
    sqlite_version: str
    cpu_architecture: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "os": self.os,
            "os_release": self.os_release,
            "python_version": self.python_version,
            "sqlite_version": self.sqlite_version,
            "cpu_architecture": self.cpu_architecture,
        }


def get_environment_info() -> EnvironmentInfo:
    return EnvironmentInfo(
        os=platform.system(),
        os_release=platform.release(),
        python_version=sys.version.split()[0],
        sqlite_version=sqlite3.sqlite_version,
        cpu_architecture=platform.machine(),
    )


class RuntimeProfiler:
    """Collects per-stage durations and memory profiles."""

    def __init__(self) -> None:
        self.profiles: list[StageProfile] = []

    @contextmanager
    def measure(self, stage_name: str) -> Generator[None, None, None]:
        tracemalloc.start()
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            _, peak_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.profiles.append(
                StageProfile(
                    stage_name=stage_name,
                    duration_ms=round(elapsed, 2),
                    peak_memory_mib=round(peak_bytes / (1024.0 * 1024.0), 3),
                )
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stages": [
                {
                    "stage": p.stage_name,
                    "duration_ms": p.duration_ms,
                    "peak_memory_mib": p.peak_memory_mib,
                }
                for p in self.profiles
            ],
            "total_duration_ms": round(sum(p.duration_ms for p in self.profiles), 2),
            "max_stage_peak_mib": round(max((p.peak_memory_mib for p in self.profiles), default=0.0), 3),
        }
