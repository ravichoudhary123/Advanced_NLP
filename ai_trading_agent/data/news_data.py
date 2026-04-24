from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests


@dataclass
class NewsProvider:
    """Simple pluggable provider. Uses Finnhub if API key is set; otherwise returns empty."""

    finnhub_api_key: str | None = None

    def get_company_news(self, symbol: str, days: int = 7) -> list[dict]:
        if not self.finnhub_api_key:
            return []
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=days)
        url = "https://finnhub.io/api/v1/company-news"
        resp = requests.get(
            url,
            params={"symbol": symbol, "from": str(start), "to": str(end), "token": self.finnhub_api_key},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def sentiment_score(self, articles: list[dict]) -> float:
        if not articles:
            return 0.0
        positive_words = {"beat", "growth", "partnership", "launch", "upgrade", "record", "expands"}
        negative_words = {"downgrade", "miss", "delay", "lawsuit", "cuts", "weak"}
        score = 0
        for a in articles:
            text = f"{a.get('headline', '')} {a.get('summary', '')}".lower()
            score += sum(w in text for w in positive_words)
            score -= sum(w in text for w in negative_words)
        return score / max(len(articles), 1)
