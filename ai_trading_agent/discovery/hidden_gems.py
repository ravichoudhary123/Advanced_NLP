from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ai_trading_agent.data.market_data import MarketDataProvider
from ai_trading_agent.data.news_data import NewsProvider


@dataclass
class HiddenGemDiscovery:
    market: MarketDataProvider
    news: NewsProvider

    def score_candidates(
        self,
        leaders: pd.DataFrame,
        candidates: pd.DataFrame,
        benchmark_symbol: str = "SOXX",
    ) -> pd.DataFrame:
        benchmark = self.market.get_ohlcv(benchmark_symbol, timeframe="1d", lookback_days=90)
        benchmark_ret = (benchmark["close"].iloc[-1] / benchmark["close"].iloc[-22]) - 1 if len(benchmark) > 30 else 0

        top_leaders = set(leaders.head(8)["symbol"].tolist()) if not leaders.empty else set()
        scored = []
        for _, row in candidates.iterrows():
            symbol = row["symbol"]
            df = self.market.get_ohlcv(symbol, timeframe="1d", lookback_days=120)
            if len(df) < 60:
                continue
            ret_1m = (df["close"].iloc[-1] / df["close"].iloc[-22]) - 1
            rel_lag = max(0.0, benchmark_ret - ret_1m)
            liquidity = min(1.0, df["dollar_volume"].tail(20).mean() / 10_000_000)
            valuation_gap = min(1.0, max(0.0, (row.get("peer_ps", 8) - row.get("ps_ratio", 8)) / 10))
            similarity = 1.0 if row.get("peer_symbol") in top_leaders else float(row.get("similarity", 0.4))
            ai_exposure = float(row.get("ai_exposure", 0.4))
            sentiment = self.news.sentiment_score(self.news.get_company_news(symbol, days=10))
            sentiment_scaled = max(0.0, min(1.0, (sentiment + 2) / 4))

            total = (
                0.25 * similarity
                + 0.2 * ai_exposure
                + 0.2 * sentiment_scaled
                + 0.15 * rel_lag
                + 0.1 * valuation_gap
                + 0.1 * liquidity
            )
            reason = (
                f"similarity={similarity:.2f}, ai_exposure={ai_exposure:.2f}, sentiment={sentiment_scaled:.2f}, "
                f"lag={rel_lag:.2f}, valuation_gap={valuation_gap:.2f}, liquidity={liquidity:.2f}"
            )
            scored.append({"symbol": symbol, "hidden_gem_score": total, "reason": reason})
        out = pd.DataFrame(scored)
        if out.empty:
            return out
        return out.sort_values("hidden_gem_score", ascending=False)
