from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf


_INTERVAL_MAP = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}


@dataclass
class MarketDataProvider:
    """Open-source market data provider based on yfinance."""

    def get_ohlcv(self, symbol: str, timeframe: str = "1d", lookback_days: int = 180) -> pd.DataFrame:
        interval = _INTERVAL_MAP.get(timeframe, "1d")
        start = datetime.utcnow() - timedelta(days=lookback_days)
        df = yf.download(symbol, start=start, interval=interval, auto_adjust=False, progress=False)
        if df.empty:
            return df
        df = df.rename(columns=str.lower)
        df = df[["open", "high", "low", "close", "volume"]].copy()
        return self.add_indicators(df)

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["ret_1"] = out["close"].pct_change()
        out["sma_20"] = out["close"].rolling(20).mean()
        out["sma_50"] = out["close"].rolling(50).mean()
        out["ema_20"] = out["close"].ewm(span=20, adjust=False).mean()
        delta = out["close"].diff()
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)
        avg_gain = pd.Series(gain, index=out.index).rolling(14).mean()
        avg_loss = pd.Series(loss, index=out.index).rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        out["rsi_14"] = 100 - (100 / (1 + rs))
        out["volatility_20"] = out["ret_1"].rolling(20).std()
        out["dollar_volume"] = out["close"] * out["volume"]
        return out
