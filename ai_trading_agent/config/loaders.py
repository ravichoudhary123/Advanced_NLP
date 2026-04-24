from __future__ import annotations

from pathlib import Path
import yaml

from ai_trading_agent.config.schema import AppConfig


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    data = yaml.safe_load(p.read_text()) if p.exists() else {}
    return AppConfig(**(data or {}))


def load_watchlist(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}
