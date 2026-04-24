from __future__ import annotations

from dataclasses import dataclass

from ai_trading_agent.core import Signal


@dataclass
class SignalFusion:
    min_confidence: float = 0.62

    def fuse(self, symbol: str, technical: dict, ml_score: float, gem_score: float, catalyst_score: float) -> Signal | None:
        score = 0.35 * technical["score"] + 0.25 * ml_score + 0.25 * gem_score + 0.15 * catalyst_score
        if score < self.min_confidence:
            return None
        reason = (
            f"technical={technical['score']:.2f}, ml={ml_score:.2f}, hidden_gem={gem_score:.2f}, "
            f"catalyst={catalyst_score:.2f}, setup={technical['setup']}"
        )
        return Signal(symbol=symbol, side="buy", confidence=score, score=score, reason=reason)
