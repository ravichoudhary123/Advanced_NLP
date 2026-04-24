from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(equity_curve: pd.Series, trades: list[dict]) -> dict:
    returns = equity_curve.pct_change().dropna()
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    years = max(len(equity_curve) / 252, 1e-9)
    cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1
    sharpe = np.sqrt(252) * returns.mean() / (returns.std() + 1e-9)
    downside = returns[returns < 0]
    sortino = np.sqrt(252) * returns.mean() / (downside.std() + 1e-9)
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max
    win_rate = sum(t["pnl"] > 0 for t in trades) / max(len(trades), 1)
    gross_profit = sum(max(t["pnl"], 0) for t in trades)
    gross_loss = abs(sum(min(t["pnl"], 0) for t in trades))
    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
        "win_rate": win_rate,
        "profit_factor": gross_profit / max(gross_loss, 1e-9),
        "turnover": len(trades) / max(len(equity_curve), 1),
        "exposure": float((returns != 0).mean()) if not returns.empty else 0.0,
    }
