"""Candidate merge, feature enrichment, and multi-signal ranking."""
from __future__ import annotations

from datetime import datetime
from math import exp

from .indexes import tokenize
from .models import Candidate, StructuredQuery


class CandidateMerger:
    """Merges route candidates by canonical document id and preserves provenance."""

    def merge(self, candidate_groups: list[list[Candidate]]) -> list[Candidate]:
        merged: dict[str, Candidate] = {}
        for group in candidate_groups:
            for candidate in group:
                doc_id = candidate.doc.doc_id
                if doc_id not in merged:
                    merged[doc_id] = Candidate(doc=candidate.doc)
                target = merged[doc_id]
                for route, score in candidate.route_scores.items():
                    target.add_route_score(route, score)
                target.matched_terms.update(candidate.matched_terms)
        return list(merged.values())


class MultiSignalRanker:
    """Practical L1/L2 ranker with transparent feature weights."""

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime.utcnow()
        self.weights = {
            "dense_score": 1.2,
            "keyword_score": 1.1,
            "title_score": 1.8,
            "metadata_score": 0.8,
            "freshness_score": 0.9,
            "source_authority": 0.5,
            "popularity": 0.3,
            "cross_encoder_score": 1.5,
        }

    def rank(self, candidates: list[Candidate], sqo: StructuredQuery, limit: int = 10) -> list[Candidate]:
        for candidate in candidates:
            self._enrich(candidate, sqo)
            candidate.score = sum(self.weights[key] * candidate.features.get(key, 0.0) for key in self.weights)
            if candidate.doc.archived:
                candidate.score -= 2.0
                candidate.explanation.append("archived demotion")
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:limit]

    def _enrich(self, candidate: Candidate, sqo: StructuredQuery) -> None:
        doc = candidate.doc
        candidate.features["dense_score"] = candidate.route_scores.get("vector", 0.0)
        candidate.features["keyword_score"] = _squash(candidate.route_scores.get("bm25", 0.0))
        candidate.features["title_score"] = _squash(candidate.route_scores.get("title", 0.0))
        candidate.features["metadata_score"] = _squash(candidate.route_scores.get("metadata", 0.0))
        candidate.features["freshness_score"] = max(_recency_score(doc.updated_at, self.now), _squash(candidate.route_scores.get("recent", 0.0)))
        candidate.features["source_authority"] = min(max(doc.source_authority, 0.0), 1.0)
        candidate.features["popularity"] = min(max(doc.popularity, 0.0), 1.0)
        candidate.features["cross_encoder_score"] = self._cross_encoder_heuristic(candidate, sqo)
        self._add_explanations(candidate)

    @staticmethod
    def _cross_encoder_heuristic(candidate: Candidate, sqo: StructuredQuery) -> float:
        query_terms = set(tokenize(sqo.normalized_query or sqo.raw_query))
        title_terms = set(tokenize(candidate.doc.title))
        body_terms = set(tokenize(candidate.doc.body))
        title_overlap = len(query_terms.intersection(title_terms)) / max(len(query_terms), 1)
        body_overlap = len(query_terms.intersection(body_terms)) / max(len(query_terms), 1)
        phrase_bonus = 0.2 if (sqo.normalized_query and sqo.normalized_query in candidate.doc.body.lower()) else 0.0
        return min(1.0, title_overlap * 0.7 + body_overlap * 0.4 + phrase_bonus)

    @staticmethod
    def _add_explanations(candidate: Candidate) -> None:
        route_labels = {
            "vector": "semantic match",
            "bm25": "keyword match",
            "title": "title/entity match",
            "metadata": "metadata filter match",
            "recent": "recent activity match",
        }
        for route, label in route_labels.items():
            if candidate.route_scores.get(route, 0.0) > 0:
                candidate.explanation.append(label)


def _squash(value: float) -> float:
    return 1.0 - exp(-max(value, 0.0))


def _recency_score(updated_at: datetime | None, now: datetime) -> float:
    if updated_at is None:
        return 0.0
    age_days = max((now - updated_at).days, 0)
    return 1.0 / (1.0 + age_days / 30.0)
