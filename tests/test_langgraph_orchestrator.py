import importlib.util

import pytest

from ai_trading_agent.agents.langgraph_orchestrator import LangGraphTradingOrchestrator
from ai_trading_agent.broker.paper import PaperBroker
from ai_trading_agent.config.schema import AppConfig
from ai_trading_agent.data.market_data import MarketDataProvider
from ai_trading_agent.data.news_data import NewsProvider
from ai_trading_agent.monitoring.audit_logger import AuditLogger


def test_langgraph_missing_dependency(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda _: None)
    orch = LangGraphTradingOrchestrator(
        config=AppConfig(),
        broker=PaperBroker(),
        market=MarketDataProvider(),
        news=NewsProvider(),
        logger=AuditLogger("storage/test-decisions.log"),
    )
    with pytest.raises(RuntimeError):
        orch._ensure_langgraph()
