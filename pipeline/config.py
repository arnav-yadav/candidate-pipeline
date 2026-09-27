"""Loads config.yaml, fingerprints it, and turns --month into the reporting window."""
from __future__ import annotations

import calendar
import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


def config_sha256(path: Path = CONFIG_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


@dataclass(frozen=True)
class Window:
    month: str          # "2026-05"
    start: date         # first day of the month
    end: date           # last day of the month = the "as of" date for the run

    @property
    def prev_month(self) -> "Window":
        y, m = self.start.year, self.start.month - 1
        if m == 0:
            y, m = y - 1, 12
        return window(f"{y:04d}-{m:02d}")


def window(month: str) -> Window:
    y, m = (int(x) for x in month.split("-"))
    return Window(month, date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1]))


def month_range(first: str, last: str) -> list[str]:
    out, w = [], window(first)
    while w.month <= last:
        out.append(w.month)
        y, m = w.start.year + (w.start.month // 12), w.start.month % 12 + 1
        w = window(f"{y:04d}-{m:02d}")
    return out
