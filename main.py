from __future__ import annotations

import pandas as pd

from ai_trading_agent.agents.langgraph_orchestrator import LangGraphTradingOrchestrator
from ai_trading_agent.agents.orchestrator import TradingOrchestrator
from ai_trading_agent.broker.paper import PaperBroker
from ai_trading_agent.config.loaders import load_config, load_watchlist
from ai_trading_agent.data.market_data import MarketDataProvider
from ai_trading_agent.data.news_data import NewsProvider
from ai_trading_agent.monitoring.audit_logger import AuditLogger


def build_candidate_df(watchlist: dict) -> pd.DataFrame:
    rows = []
    for domain, items in watchlist.get("adjacent_candidates", {}).items():
        for it in items:
            it = dict(it)
            it["domain"] = domain
            rows.append(it)
    return pd.DataFrame(rows)


def main(config_path: str = "configs/config.example.yaml") -> None:
    cfg = load_config(config_path)
    watchlist = load_watchlist(cfg.leaders_watchlist_file)

    broker = PaperBroker(starting_cash=cfg.account_starting_cash, cash=cfg.account_starting_cash)
    market = MarketDataProvider()
    news = NewsProvider()
    logger = AuditLogger("storage/decisions.log")

    leaders_universe = watchlist.get("ai_leaders", [])
    candidates = build_candidate_df(watchlist)

    orchestrator = TradingOrchestrator(cfg, broker, market, news, logger)
    if cfg.execution.orchestration_engine == "langgraph":
        orchestrator = LangGraphTradingOrchestrator(cfg, broker, market, news, logger)
    result = orchestrator.run_cycle(leaders_universe, candidates)
    print("Top hidden gems:\n", result["hidden_gems"].head(5))
    print(f"Orders submitted: {len(result['orders'])}")


if __name__ == "__main__":
    main()
