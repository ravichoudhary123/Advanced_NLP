"""Rule-based query-understanding implementation for enterprise search."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import Intent, StructuredQuery

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_/-]*")


@dataclass
class QueryUnderstandingService:
    """Produces a structured query object (SQO).

    The implementation is intentionally transparent: production systems can swap
    this class for an ML/LLM classifier while keeping the same SQO contract.
    """

    acronym_map: dict[str, str] = field(default_factory=lambda: {"fnol": "first notice of loss"})
    known_sources: tuple[str, ...] = ("sharepoint", "confluence", "slack", "ado", "github", "outlook")
    now: datetime | None = None

    def understand(self, query: str) -> StructuredQuery:
        raw = query.strip()
        lowered = raw.lower()
        filters = self._extract_filters(lowered)
        source = self._extract_source(lowered)
        freshness_days = self._extract_freshness_days(lowered)
        expanded = self._expand_acronyms(lowered)
        normalized = self._normalize(lowered, expanded)
        entities = self._extract_entities(raw)
        intent = self._detect_intent(lowered, freshness_days, source, filters)
        plan = self._plan(intent, bool(filters), source)
        return StructuredQuery(
            raw_query=raw,
            normalized_query=normalized,
            intent=intent,
            entities=tuple(entities),
            expanded_terms=tuple(expanded),
            freshness_days=freshness_days,
            source_preference=source,
            filters=filters,
            retrieval_plan=plan,
        )

    def _expand_acronyms(self, lowered: str) -> list[str]:
        tokens = _TOKEN_RE.findall(lowered)
        return [self.acronym_map[token] for token in tokens if token in self.acronym_map]

    def _normalize(self, lowered: str, expanded: list[str]) -> str:
        text = re.sub(r"\b(last week|this week|latest|recent|newest|updated|from:\w+|source:\w+)\b", " ", lowered)
        for acronym, expansion in self.acronym_map.items():
            text = re.sub(rf"\b{re.escape(acronym)}\b", expansion, text)
        text = " ".join(_TOKEN_RE.findall(text))
        return " ".join([text, *expanded]).strip()

    @staticmethod
    def _extract_entities(raw: str) -> list[str]:
        entities: list[str] = []
        for match in re.finditer(r"\b[A-Z][A-Z0-9]{1,}\b", raw):
            entities.append(match.group(0))
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", raw)
        entities.extend(quoted)
        return entities

    def _extract_source(self, lowered: str) -> str | None:
        explicit = re.search(r"\b(?:from|source):(\w+)\b", lowered)
        if explicit and explicit.group(1) in self.known_sources:
            return explicit.group(1)
        for source in self.known_sources:
            if re.search(rf"\b{re.escape(source)}\b", lowered):
                return source
        return None

    @staticmethod
    def _extract_freshness_days(lowered: str) -> int | None:
        if any(term in lowered for term in ("latest", "recent", "newest", "updated")):
            return 30
        if "last week" in lowered:
            return 7
        if "this week" in lowered:
            return 7
        match = re.search(r"last (\d+) days", lowered)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_filters(lowered: str) -> dict[str, str]:
        filters: dict[str, str] = {}
        for key in ("author", "team", "department", "bu", "type", "tag"):
            match = re.search(rf"\b{key}:([\w-]+)\b", lowered)
            if match:
                mapped = {"team": "owner_team", "bu": "business_unit", "type": "doc_type", "tag": "tags"}.get(key, key)
                filters[mapped] = match.group(1)
        return filters

    @staticmethod
    def _detect_intent(lowered: str, freshness_days: int | None, source: str | None, filters: dict[str, str]) -> Intent:
        if "activity" in lowered or "last week" in lowered:
            return Intent.RECENT_ACTIVITY
        if freshness_days is not None:
            return Intent.FRESH_LOOKUP
        if filters or source:
            return Intent.METADATA_FILTER
        tokens = _TOKEN_RE.findall(lowered)
        if len(tokens) <= 3:
            return Intent.EXACT_LOOKUP
        return Intent.GENERAL

    @staticmethod
    def _plan(intent: Intent, has_filters: bool, source: str | None) -> tuple[str, ...]:
        plan = ["title", "bm25", "vector"]
        if has_filters or source:
            plan.append("metadata")
        if intent in {Intent.FRESH_LOOKUP, Intent.RECENT_ACTIVITY}:
            plan.append("recent")
        return tuple(dict.fromkeys(plan))


def freshness_cutoff(now: datetime, freshness_days: int | None) -> datetime | None:
    """Return the lower-bound timestamp for a freshness window."""

    if freshness_days is None:
        return None
    return now - timedelta(days=freshness_days)
