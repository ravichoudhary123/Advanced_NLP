from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ai_trading_agent.config.schema import RiskConfig
from ai_trading_agent.core import AccountState, Signal, TradeDecision


@dataclass
class RiskEngine:
    config: RiskConfig

    def _drawdown(self, account: AccountState) -> float:
        if account.peak_equity <= 0:
            return 0.0
        return max(0.0, (account.peak_equity - account.equity) / account.peak_equity)

    def validate_signal(
        self,
        signal: Signal,
        account: AccountState,
        last_price: float,
        avg_dollar_volume: float,
        tradable: bool,
        market_open: bool,
        data_quality_ok: bool,
    ) -> TradeDecision | None:
        checks = {}
        if not data_quality_ok:
            checks["circuit_breaker"] = "blocked: data quality uncertain"
            return None
        if not tradable:
            checks["tradable"] = "blocked: symbol not tradable"
            return None
        if avg_dollar_volume < self.config.min_dollar_volume:
            checks["liquidity"] = "blocked: illiquid"
            return None
        if self._drawdown(account) > self.config.max_drawdown_pct:
            checks["drawdown"] = "blocked: max drawdown exceeded"
            return None
        if account.day_pnl < -account.equity * self.config.daily_loss_stop_pct:
            checks["daily_loss"] = "blocked: daily stop reached"
            return None
        if not market_open:
            checks["hours"] = "blocked: market closed"
            return None

        open_positions = sum(1 for q in account.positions.values() if q > 0)
        if open_positions >= self.config.max_open_positions and signal.symbol not in account.positions:
            checks["positions"] = "blocked: max positions"
            return None

        max_trade_value = account.equity * self.config.max_trade_pct
        max_symbol_value = account.equity * self.config.max_symbol_pct
        current_symbol_value = account.positions.get(signal.symbol, 0) * last_price
        allowable_symbol_add = max(0.0, max_symbol_value - current_symbol_value)
        target_value = min(max_trade_value, allowable_symbol_add, account.cash)
        qty = int(target_value // last_price)

        if qty <= 0:
            checks["cash"] = "blocked: insufficient settled cash or sizing cap"
            return None

        est_cost = qty * last_price
        if est_cost > account.cash:
            checks["cash"] = "blocked: would exceed cash"
            return None

        checks.update(
            {
                "cash_only": "pass",
                "no_margin": "pass",
                "position_sizing": f"pass qty={qty}",
            }
        )
        explanation = (
            f"BUY {signal.symbol}: {signal.reason}. risk_checks={checks}; cash={account.cash:.2f}; "
            f"est_cost={est_cost:.2f}"
        )
        return TradeDecision(symbol=signal.symbol, qty=qty, side="buy", limit_price=last_price, explanation=explanation, checks=checks)
