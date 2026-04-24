from __future__ import annotations

from dataclasses import dataclass
import importlib.util

import pandas as pd

from ai_trading_agent.broker.base import Broker
from ai_trading_agent.config.schema import AppConfig
from ai_trading_agent.data.market_data import MarketDataProvider
from ai_trading_agent.data.news_data import NewsProvider
from ai_trading_agent.discovery.hidden_gems import HiddenGemDiscovery
from ai_trading_agent.discovery.sector_leaders import SectorLeaderDetector
from ai_trading_agent.monitoring.audit_logger import AuditLogger
from ai_trading_agent.risk.engine import RiskEngine
from ai_trading_agent.signals.ml_ranker import MLPatternRanker
from ai_trading_agent.signals.signal_fusion import SignalFusion
from ai_trading_agent.signals.technical import TechnicalSignalEngine


@dataclass
class LangGraphTradingOrchestrator:
    """Optional orchestration layer using LangGraph StateGraph.

    This preserves the same hard-risk checks and execution policies as the native orchestrator.
    """

    config: AppConfig
    broker: Broker
    market: MarketDataProvider
    news: NewsProvider
    logger: AuditLogger

    def _ensure_langgraph(self) -> None:
        if importlib.util.find_spec("langgraph.graph") is None:
            raise RuntimeError(
                "LangGraph is not installed. Install optional dependency: pip install langgraph"
            )

    def run_cycle(self, leaders_universe: list[str], candidate_df: pd.DataFrame) -> dict:
        self._ensure_langgraph()
        from langgraph.graph import END, StateGraph

        state: dict = {
            "leaders_universe": leaders_universe,
            "candidate_df": candidate_df,
            "leaders": pd.DataFrame(),
            "hidden": pd.DataFrame(),
            "orders": [],
        }

        leader_agent = SectorLeaderDetector(self.market)
        hidden_agent = HiddenGemDiscovery(self.market, self.news)
        tech_agent = TechnicalSignalEngine()
        ml_agent = MLPatternRanker()
        fusion = SignalFusion()
        risk = RiskEngine(self.config.risk)

        def detect_leaders(s: dict) -> dict:
            s["leaders"] = leader_agent.detect(s["leaders_universe"])
            return s

        def discover_hidden_gems(s: dict) -> dict:
            s["hidden"] = hidden_agent.score_candidates(s["leaders"], s["candidate_df"])
            return s

        def generate_and_execute(s: dict) -> dict:
            account = self.broker.get_account()
            decisions = []
            for _, row in s["hidden"].head(10).iterrows():
                symbol = row["symbol"]
                bars = self.market.get_ohlcv(symbol, timeframe="1d", lookback_days=self.config.data.lookback_days)
                if bars.empty:
                    continue
                bars["target"] = (bars["close"].shift(-5) / bars["close"] - 1).fillna(0).clip(-1, 1)
                ml_agent.train(bars)
                ml_score = ml_agent.predict_score(bars)
                technical = tech_agent.generate(symbol, bars)
                catalyst = max(0.0, min(1.0, (self.news.sentiment_score(self.news.get_company_news(symbol, 10)) + 2) / 4))
                signal = fusion.fuse(symbol, technical, ml_score, float(row["hidden_gem_score"]), catalyst)
                if signal is None:
                    continue
                decision = risk.validate_signal(
                    signal=signal,
                    account=account,
                    last_price=float(bars["close"].iloc[-1]),
                    avg_dollar_volume=float(bars["dollar_volume"].tail(20).mean()),
                    tradable=self.broker.is_tradable(symbol),
                    market_open=True,
                    data_quality_ok=True,
                )
                if decision is None:
                    self.logger.log("trade_rejected", {"symbol": symbol, "reason": "risk validation failed"})
                    continue
                result = self.broker.place_order(decision)
                self.logger.log(
                    "order_event",
                    {
                        "decision": decision.__dict__,
                        "result": result.__dict__,
                        "hidden_gem_reason": row["reason"],
                    },
                )
                decisions.append({"symbol": symbol, "decision": decision, "result": result})
            s["orders"] = decisions
            return s

        graph = StateGraph(dict)
        graph.add_node("leaders", detect_leaders)
        graph.add_node("hidden_gems", discover_hidden_gems)
        graph.add_node("execute", generate_and_execute)
        graph.set_entry_point("leaders")
        graph.add_edge("leaders", "hidden_gems")
        graph.add_edge("hidden_gems", "execute")
        graph.add_edge("execute", END)

        app = graph.compile()
        out = app.invoke(state)
        return {"leaders": out["leaders"], "hidden_gems": out["hidden"], "orders": out["orders"]}
