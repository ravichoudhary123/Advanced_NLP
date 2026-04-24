from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Signal:
    symbol: str
    side: str
    confidence: float
    score: float
    reason: str
    target_price: float | None = None
    stop_price: float | None = None


@dataclass
class TradeDecision:
    symbol: str
    qty: int
    side: str
    limit_price: float | None
    explanation: str
    checks: dict[str, str] = field(default_factory=dict)


@dataclass
class AccountState:
    cash: float
    equity: float
    buying_power: float
    positions: dict[str, int]
    day_pnl: float = 0.0
    peak_equity: float = 0.0


@dataclass
class OrderResult:
    accepted: bool
    order_id: str
    message: str
    timestamp: datetime
