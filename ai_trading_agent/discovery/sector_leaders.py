from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_trading_agent.data.market_data import MarketDataProvider


@dataclass
class SectorLeaderDetector:
    market: MarketDataProvider

    def detect(self, symbols: list[str], lookback_days: int = 60) -> pd.DataFrame:
        rows = []
        for s in symbols:
            df = self.market.get_ohlcv(s, timeframe="1d", lookback_days=lookback_days)
            if len(df) < 30:
                continue
            ret_1m = (df["close"].iloc[-1] / df["close"].iloc[-22]) - 1
            ret_3m = (df["close"].iloc[-1] / df["close"].iloc[0]) - 1
            momentum = (df["ema_20"].iloc[-1] / df["sma_50"].iloc[-1]) - 1 if pd.notna(df["sma_50"].iloc[-1]) else 0
            rows.append({"symbol": s, "ret_1m": ret_1m, "ret_3m": ret_3m, "momentum": momentum})
        out = pd.DataFrame(rows)
        if out.empty:
            return out
        out["leader_score"] = 0.45 * out["ret_1m"] + 0.35 * out["ret_3m"] + 0.20 * out["momentum"]
        return out.sort_values("leader_score", ascending=False)
