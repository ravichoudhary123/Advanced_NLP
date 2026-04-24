from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_trading_agent.backtest.metrics import compute_metrics


@dataclass
class BacktestConfig:
    initial_cash: float = 100_000
    trade_fee_bps: float = 5
    slippage_bps: float = 10


@dataclass
class BacktestEngine:
    config: BacktestConfig = BacktestConfig()

    def run(self, price_df: pd.DataFrame, signals: pd.Series) -> dict:
        cash = self.config.initial_cash
        qty = 0
        equity_curve = []
        trades = []
        for dt, row in price_df.iterrows():
            px = row["close"] * (1 + self.config.slippage_bps / 10_000)
            signal = int(signals.get(dt, 0))
            if signal == 1 and qty == 0:
                buy_qty = int(cash // px)
                if buy_qty > 0:
                    notional = buy_qty * px
                    fee = notional * self.config.trade_fee_bps / 10_000
                    cash -= notional + fee
                    qty = buy_qty
                    trades.append({"time": dt, "type": "buy", "qty": buy_qty, "price": px, "pnl": 0.0})
            elif signal == -1 and qty > 0:
                sell_notional = qty * px
                fee = sell_notional * self.config.trade_fee_bps / 10_000
                entry = next(t for t in reversed(trades) if t["type"] == "buy")
                pnl = (px - entry["price"]) * qty - fee
                cash += sell_notional - fee
                trades.append({"time": dt, "type": "sell", "qty": qty, "price": px, "pnl": pnl})
                qty = 0
            equity = cash + qty * row["close"]
            equity_curve.append((dt, equity))

        curve = pd.Series(dict(equity_curve)).sort_index()
        metrics = compute_metrics(curve, [t for t in trades if t["type"] == "sell"])
        return {"equity_curve": curve, "trades": trades, "metrics": metrics}
