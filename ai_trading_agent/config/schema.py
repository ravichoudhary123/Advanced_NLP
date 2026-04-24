from __future__ import annotations

from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    max_trade_pct: float = Field(default=0.05, ge=0.0, le=1.0)
    max_symbol_pct: float = Field(default=0.15, ge=0.0, le=1.0)
    daily_loss_stop_pct: float = Field(default=0.03, ge=0.0, le=1.0)
    max_drawdown_pct: float = Field(default=0.15, ge=0.0, le=1.0)
    max_open_positions: int = Field(default=8, ge=1)
    min_dollar_volume: float = 2_000_000
    stop_loss_pct: float = 0.06
    take_profit_pct: float = 0.15
    trailing_stop_pct: float = 0.05


class ExecutionConfig(BaseModel):
    mode: str = "paper"  # paper or live
    allow_live: bool = False
    market_hours_only: bool = True
    orchestration_engine: str = "native"  # native or langgraph


class DataConfig(BaseModel):
    benchmark_symbols: list[str] = ["SPY", "QQQ", "SOXX"]
    timeframes: list[str] = ["1m", "5m", "15m", "1h", "1d"]
    lookback_days: int = 120


class AppConfig(BaseModel):
    account_starting_cash: float = 100_000
    leaders_watchlist_file: str = "configs/watchlist.example.yaml"
    risk: RiskConfig = RiskConfig()
    execution: ExecutionConfig = ExecutionConfig()
    data: DataConfig = DataConfig()
