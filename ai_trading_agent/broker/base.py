from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trading_agent.core import AccountState, OrderResult, TradeDecision


class Broker(ABC):
    @abstractmethod
    def get_account(self) -> AccountState:
        raise NotImplementedError

    @abstractmethod
    def is_tradable(self, symbol: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, decision: TradeDecision) -> OrderResult:
        raise NotImplementedError
