from ai_trading_agent.config.schema import RiskConfig
from ai_trading_agent.core import AccountState, Signal
from ai_trading_agent.risk.engine import RiskEngine


def test_risk_engine_blocks_overspend():
    engine = RiskEngine(RiskConfig(max_trade_pct=0.5, max_symbol_pct=0.5))
    account = AccountState(cash=1000, equity=1000, buying_power=1000, positions={}, peak_equity=1000)
    signal = Signal(symbol="ABC", side="buy", confidence=0.9, score=0.9, reason="test")
    decision = engine.validate_signal(signal, account, last_price=2000, avg_dollar_volume=5_000_000, tradable=True, market_open=True, data_quality_ok=True)
    assert decision is None


def test_risk_engine_cash_only_pass():
    engine = RiskEngine(RiskConfig(max_trade_pct=0.2, max_symbol_pct=0.2))
    account = AccountState(cash=10000, equity=10000, buying_power=10000, positions={}, peak_equity=10000)
    signal = Signal(symbol="ABC", side="buy", confidence=0.9, score=0.9, reason="test")
    decision = engine.validate_signal(signal, account, last_price=100, avg_dollar_volume=5_000_000, tradable=True, market_open=True, data_quality_ok=True)
    assert decision is not None
    assert decision.qty <= 20
