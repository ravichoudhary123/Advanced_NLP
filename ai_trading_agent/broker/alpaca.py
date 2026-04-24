from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from ai_trading_agent.broker.base import Broker
from ai_trading_agent.core import AccountState, OrderResult, TradeDecision


@dataclass
class AlpacaBroker(Broker):
    key_id: str
    secret_key: str
    base_url: str = "https://paper-api.alpaca.markets"

    def _headers(self) -> dict[str, str]:
        return {"APCA-API-KEY-ID": self.key_id, "APCA-API-SECRET-KEY": self.secret_key}

    def get_account(self) -> AccountState:
        r = requests.get(f"{self.base_url}/v2/account", headers=self._headers(), timeout=20)
        r.raise_for_status()
        a = r.json()
        return AccountState(
            cash=float(a["cash"]),
            equity=float(a["equity"]),
            buying_power=float(a["cash"]),
            positions={},
            day_pnl=float(a.get("equity", 0)) - float(a.get("last_equity", a.get("equity", 0))),
            peak_equity=float(a.get("equity", 0)),
        )

    def is_tradable(self, symbol: str) -> bool:
        r = requests.get(f"{self.base_url}/v2/assets/{symbol}", headers=self._headers(), timeout=20)
        if not r.ok:
            return False
        asset = r.json()
        return bool(asset.get("tradable", False)) and asset.get("marginable", False) is False

    def place_order(self, decision: TradeDecision) -> OrderResult:
        payload = {
            "symbol": decision.symbol,
            "qty": decision.qty,
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
        }
        r = requests.post(f"{self.base_url}/v2/orders", json=payload, headers=self._headers(), timeout=20)
        if not r.ok:
            return OrderResult(False, "", r.text, datetime.now(timezone.utc))
        order = r.json()
        return OrderResult(True, order.get("id", ""), "submitted", datetime.now(timezone.utc))
