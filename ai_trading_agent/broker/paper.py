from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid

from ai_trading_agent.broker.base import Broker
from ai_trading_agent.core import AccountState, OrderResult, TradeDecision


@dataclass
class PaperBroker(Broker):
    starting_cash: float = 100_000
    cash: float = 100_000
    positions: dict[str, int] = field(default_factory=dict)
    prices: dict[str, float] = field(default_factory=dict)

    def mark_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price

    def get_account(self) -> AccountState:
        equity = self.cash + sum(self.positions.get(s, 0) * self.prices.get(s, 0) for s in self.positions)
        return AccountState(
            cash=self.cash,
            equity=equity,
            buying_power=self.cash,
            positions=dict(self.positions),
            day_pnl=equity - self.starting_cash,
            peak_equity=max(self.starting_cash, equity),
        )

    def is_tradable(self, symbol: str) -> bool:
        return True

    def place_order(self, decision: TradeDecision) -> OrderResult:
        px = decision.limit_price or self.prices.get(decision.symbol)
        if px is None:
            return OrderResult(False, "", "missing price", datetime.now(timezone.utc))
        cost = px * decision.qty
        if cost > self.cash:
            return OrderResult(False, "", "insufficient cash", datetime.now(timezone.utc))

        self.cash -= cost
        self.positions[decision.symbol] = self.positions.get(decision.symbol, 0) + decision.qty
        return OrderResult(True, str(uuid.uuid4()), f"filled {decision.qty} {decision.symbol} @ {px}", datetime.now(timezone.utc))
