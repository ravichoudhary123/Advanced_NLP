from __future__ import annotations

from dataclasses import dataclass

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
class TradingOrchestrator:
    config: AppConfig
    broker: Broker
    market: MarketDataProvider
    news: NewsProvider
    logger: AuditLogger

    def run_cycle(self, leaders_universe: list[str], candidate_df: pd.DataFrame) -> dict:
        leader_agent = SectorLeaderDetector(self.market)
        hidden_agent = HiddenGemDiscovery(self.market, self.news)
        tech_agent = TechnicalSignalEngine()
        ml_agent = MLPatternRanker()
        fusion = SignalFusion()
        risk = RiskEngine(self.config.risk)

        leaders = leader_agent.detect(leaders_universe)
        hidden = hidden_agent.score_candidates(leaders, candidate_df)

        account = self.broker.get_account()
        decisions = []
        for _, row in hidden.head(10).iterrows():
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

            last_price = float(bars["close"].iloc[-1])
            avg_dv = float(bars["dollar_volume"].tail(20).mean())
            decision = risk.validate_signal(
                signal=signal,
                account=account,
                last_price=last_price,
                avg_dollar_volume=avg_dv,
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

        return {"leaders": leaders, "hidden_gems": hidden, "orders": decisions}
