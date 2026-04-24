import pandas as pd

from ai_trading_agent.data.market_data import MarketDataProvider
from ai_trading_agent.data.news_data import NewsProvider
from ai_trading_agent.discovery.hidden_gems import HiddenGemDiscovery


class DummyMarket(MarketDataProvider):
    def get_ohlcv(self, symbol: str, timeframe: str = "1d", lookback_days: int = 180):
        idx = pd.date_range("2024-01-01", periods=100)
        close = pd.Series(range(100), index=idx) + 100
        return pd.DataFrame({"open": close, "high": close, "low": close, "close": close, "volume": 1_000_000, "dollar_volume": close * 1_000_000})


class DummyNews(NewsProvider):
    def get_company_news(self, symbol: str, days: int = 7):
        return [{"headline": "record growth partnership launch"}]


def test_hidden_gem_scoring_runs():
    leaders = pd.DataFrame([{"symbol": "NVDA"}])
    candidates = pd.DataFrame([
        {"symbol": "SMCI", "peer_symbol": "NVDA", "ai_exposure": 0.8, "ps_ratio": 2.0, "peer_ps": 10.0, "similarity": 0.7}
    ])
    discovery = HiddenGemDiscovery(DummyMarket(), DummyNews())
    out = discovery.score_candidates(leaders, candidates)
    assert not out.empty
    assert "hidden_gem_score" in out.columns
