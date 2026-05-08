"""In-memory retrieval indexes for the enterprise search/RAG implementation."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable

from .models import ActivityEvent, Candidate, Document, StructuredQuery
from .query_understanding import freshness_cutoff

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_/-]*")


def tokenize(text: str) -> list[str]:
    """Normalize text into search tokens."""

    return _TOKEN_RE.findall(text.lower())


def cosine(a: Counter[str], b: Counter[str]) -> float:
    """Sparse cosine similarity used as a deterministic vector-search stand-in."""

    if not a or not b:
        return 0.0
    dot = sum(a[token] * b.get(token, 0) for token in a)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


class DocumentStore:
    """Canonical in-memory document store."""

    def __init__(self, documents: Iterable[Document] = ()) -> None:
        self.documents: dict[str, Document] = {}
        for doc in documents:
            self.add(doc)

    def add(self, doc: Document) -> None:
        self.documents[doc.doc_id] = doc

    def get(self, doc_id: str) -> Document | None:
        return self.documents.get(doc_id)

    def all(self) -> list[Document]:
        return list(self.documents.values())


class VectorIndex:
    """Semantic retrieval over document text using sparse embeddings."""

    route_name = "vector"

    def __init__(self, documents: Iterable[Document]) -> None:
        self.embeddings = {doc.doc_id: Counter(tokenize(f"{doc.title} {doc.body}")) for doc in documents}
        self.documents = {doc.doc_id: doc for doc in documents}

    def search(self, sqo: StructuredQuery, top_k: int = 20) -> list[Candidate]:
        query_vector = Counter(tokenize(sqo.normalized_query))
        scored = []
        for doc_id, vector in self.embeddings.items():
            score = cosine(query_vector, vector)
            if score > 0:
                scored.append((score, self.documents[doc_id]))
        return _to_candidates(self.route_name, scored, top_k)


class BM25Index:
    """Keyword/BM25 retrieval for rare terms, exact phrases, and acronyms."""

    route_name = "bm25"

    def __init__(self, documents: Iterable[Document]) -> None:
        self.documents = {doc.doc_id: doc for doc in documents}
        self.doc_tokens = {
            doc.doc_id: tokenize(f"{doc.title} {doc.title} {doc.body} {' '.join(doc.tags)}") for doc in documents
        }
        self.doc_freq: Counter[str] = Counter()
        for tokens in self.doc_tokens.values():
            self.doc_freq.update(set(tokens))
        self.avg_len = sum(len(tokens) for tokens in self.doc_tokens.values()) / max(len(self.doc_tokens), 1)

    def search(self, sqo: StructuredQuery, top_k: int = 20) -> list[Candidate]:
        query_terms = tokenize(sqo.normalized_query or sqo.raw_query)
        scored: list[tuple[float, Document]] = []
        for doc_id, tokens in self.doc_tokens.items():
            score = self._score(query_terms, tokens)
            if score > 0:
                scored.append((score, self.documents[doc_id]))
        return _to_candidates(self.route_name, scored, top_k)

    def _score(self, query_terms: list[str], doc_terms: list[str], k1: float = 1.2, b: float = 0.75) -> float:
        counts = Counter(doc_terms)
        score = 0.0
        total_docs = max(len(self.doc_tokens), 1)
        for term in query_terms:
            if term not in counts:
                continue
            df = self.doc_freq.get(term, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            tf = counts[term]
            denom = tf + k1 * (1 - b + b * len(doc_terms) / max(self.avg_len, 1))
            score += idf * (tf * (k1 + 1)) / denom
        return score


class MetadataIndex:
    """Structured filtering and faceting over normalized document metadata."""

    route_name = "metadata"

    def __init__(self, documents: Iterable[Document]) -> None:
        self.documents = list(documents)

    def search(self, sqo: StructuredQuery, top_k: int = 50) -> list[Candidate]:
        if not sqo.filters and not sqo.source_preference:
            return []
        scored: list[tuple[float, Document]] = []
        for doc in self.documents:
            score = self._match_score(doc, sqo)
            if score > 0:
                scored.append((score, doc))
        return _to_candidates(self.route_name, scored, top_k)

    def facets(self, docs: Iterable[Document]) -> dict[str, dict[str, int]]:
        facet_fields = ("source", "doc_type", "owner_team", "business_unit", "department")
        facets: dict[str, dict[str, int]] = {}
        for field in facet_fields:
            counts: Counter[str] = Counter()
            for doc in docs:
                value = getattr(doc, field)
                if value:
                    counts[str(value)] += 1
            facets[field] = dict(counts.most_common(20))
        return facets

    @staticmethod
    def _match_score(doc: Document, sqo: StructuredQuery) -> float:
        score = 0.0
        if sqo.source_preference and doc.source == sqo.source_preference:
            score += 1.0
        for key, expected in sqo.filters.items():
            value = getattr(doc, key, None)
            if key == "tags" and expected in doc.tags:
                score += 1.0
            elif value and str(value).lower() == str(expected).lower():
                score += 1.0
        return score


class TitleEntityIndex:
    """Exact, alias, prefix, and conservative fuzzy title/entity lookup."""

    route_name = "title"

    def __init__(self, documents: Iterable[Document]) -> None:
        self.documents = list(documents)

    def search(self, sqo: StructuredQuery, top_k: int = 20) -> list[Candidate]:
        query = " ".join(tokenize(sqo.normalized_query or sqo.raw_query))
        raw = " ".join(tokenize(sqo.raw_query))
        scored: list[tuple[float, Document]] = []
        for doc in self.documents:
            variants = [doc.title, *doc.aliases, *doc.tags]
            best = max((self._variant_score(raw, query, variant) for variant in variants), default=0.0)
            if best > 0:
                scored.append((best, doc))
        return _to_candidates(self.route_name, scored, top_k)

    @staticmethod
    def _variant_score(raw: str, query: str, variant: str) -> float:
        normalized = " ".join(tokenize(variant))
        if not normalized:
            return 0.0
        if raw == normalized or query == normalized:
            return 3.0
        if normalized.startswith(raw) or raw.startswith(normalized):
            return 2.0
        query_terms = set(tokenize(query or raw))
        variant_terms = set(tokenize(normalized))
        overlap = len(query_terms.intersection(variant_terms)) / max(len(query_terms), 1)
        return 1.0 + overlap if overlap >= 0.6 else 0.0


class RecentActivityIndex:
    """Freshness-oriented event retrieval."""

    route_name = "recent"

    def __init__(self, documents: Iterable[Document], events: Iterable[ActivityEvent], now: datetime | None = None) -> None:
        self.documents = {doc.doc_id: doc for doc in documents}
        self.events = list(events)
        self.now = now or datetime.utcnow()

    def search(self, sqo: StructuredQuery, top_k: int = 20) -> list[Candidate]:
        cutoff = freshness_cutoff(self.now, sqo.freshness_days) if sqo.freshness_days else None
        query_terms = set(tokenize(sqo.normalized_query or sqo.raw_query))
        scored_by_doc: dict[str, float] = defaultdict(float)
        for event in self.events:
            if cutoff and event.event_time < cutoff:
                continue
            doc = self.documents.get(event.doc_id)
            if not doc:
                continue
            haystack = set(tokenize(f"{event.activity_text} {doc.title} {doc.body}"))
            overlap = len(query_terms.intersection(haystack)) / max(len(query_terms), 1)
            recency = 1.0 / (1.0 + max((self.now - event.event_time).days, 0))
            score = overlap + recency
            if score > 0:
                scored_by_doc[event.doc_id] = max(scored_by_doc[event.doc_id], score)
        scored = [(score, self.documents[doc_id]) for doc_id, score in scored_by_doc.items()]
        return _to_candidates(self.route_name, scored, top_k)


def _to_candidates(route: str, scored: list[tuple[float, Document]], top_k: int) -> list[Candidate]:
    candidates: list[Candidate] = []
    for score, doc in sorted(scored, key=lambda item: item[0], reverse=True)[:top_k]:
        candidate = Candidate(doc=doc)
        candidate.add_route_score(route, float(score))
        candidates.append(candidate)
    return candidates
