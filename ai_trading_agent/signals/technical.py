from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class TechnicalSignalEngine:
    def generate(self, symbol: str, df: pd.DataFrame) -> dict:
        if len(df) < 60:
            return {"symbol": symbol, "score": 0.0, "setup": "insufficient_data", "bullish": False}

        latest = df.iloc[-1]
        bullish_trend = latest["close"] > latest["sma_20"] > latest["sma_50"]
        bullish_momentum = latest["rsi_14"] > 50 and latest["rsi_14"] < 75
        volume_confirm = latest["volume"] > df["volume"].tail(20).mean()

        score = float(bullish_trend) * 0.45 + float(bullish_momentum) * 0.35 + float(volume_confirm) * 0.2
        return {
            "symbol": symbol,
            "score": score,
            "setup": f"trend={bullish_trend}, momentum={bullish_momentum}, volume={volume_confirm}",
            "bullish": score >= 0.6,
        }
