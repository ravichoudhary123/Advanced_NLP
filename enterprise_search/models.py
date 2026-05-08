"""Core data models for the enterprise search/RAG reference implementation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Intent(str, Enum):
    """Supported high-level query intents."""

    GENERAL = "general_search"
    EXACT_LOOKUP = "exact_lookup"
    FRESH_LOOKUP = "fresh_lookup"
    RECENT_ACTIVITY = "recent_activity"
    METADATA_FILTER = "metadata_filter"


@dataclass(frozen=True)
class ACL:
    """Document-level access-control metadata.

    Deny entries always win over allow entries. Public documents are still
    constrained by tenant and archived filtering in the search service.
    """

    public: bool = False
    allow_users: frozenset[str] = frozenset()
    allow_groups: frozenset[str] = frozenset()
    deny_users: frozenset[str] = frozenset()
    deny_groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class UserContext:
    """Resolved identity and entitlement context for one request."""

    user_id: str
    groups: frozenset[str] = frozenset()
    tenant: str = "default"
    source_tokens: dict[str, str] = field(default_factory=dict)


@dataclass
class Document:
    """Canonical enterprise document representation used by all indexes."""

    doc_id: str
    title: str
    body: str
    source: str
    url: str
    acl: ACL
    tenant: str = "default"
    author: str | None = None
    owner_team: str | None = None
    business_unit: str | None = None
    department: str | None = None
    doc_type: str | None = None
    tags: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived: bool = False
    popularity: float = 0.0
    source_authority: float = 1.0
    aliases: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActivityEvent:
    """Recent activity event with its own permission-aware document reference."""

    event_id: str
    doc_id: str
    event_type: str
    event_time: datetime
    activity_text: str
    actor_id: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class StructuredQuery:
    """Normalized query-understanding output consumed by retrieval and ranking."""

    raw_query: str
    normalized_query: str
    intent: Intent
    entities: tuple[str, ...] = ()
    expanded_terms: tuple[str, ...] = ()
    freshness_days: int | None = None
    source_preference: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    retrieval_plan: tuple[str, ...] = ("vector", "bm25", "metadata", "title", "recent")


@dataclass
class Candidate:
    """Search candidate accumulated across retrieval routes."""

    doc: Document
    route_scores: dict[str, float] = field(default_factory=dict)
    matched_terms: set[str] = field(default_factory=set)
    features: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    explanation: list[str] = field(default_factory=list)

    def add_route_score(self, route: str, score: float) -> None:
        self.route_scores[route] = max(score, self.route_scores.get(route, 0.0))


@dataclass(frozen=True)
class Citation:
    """Grounding citation returned with an answer."""

    doc_id: str
    title: str
    url: str
    source: str


@dataclass(frozen=True)
class SearchResult:
    """User-facing ranked search result."""

    doc_id: str
    title: str
    url: str
    source: str
    score: float
    snippet: str
    updated_at: datetime | None
    explanation: tuple[str, ...]


@dataclass(frozen=True)
class Answer:
    """Grounded RAG response."""

    text: str
    citations: tuple[Citation, ...]
    confidence: float
    no_answer: bool = False


@dataclass(frozen=True)
class SearchResponse:
    """Full response from the enterprise search service."""

    query: StructuredQuery
    answer: Answer
    results: tuple[SearchResult, ...]
    facets: dict[str, dict[str, int]]
    trace: dict[str, Any]
