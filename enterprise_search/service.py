"""Composable enterprise search and RAG service."""
from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Iterable

from .indexes import BM25Index, DocumentStore, MetadataIndex, RecentActivityIndex, TitleEntityIndex, VectorIndex
from .models import ActivityEvent, Candidate, Document, SearchResponse, SearchResult, UserContext
from .permissions import EntitlementService
from .query_understanding import QueryUnderstandingService
from .rag import GroundedAnswerService
from .ranking import CandidateMerger, MultiSignalRanker


class EnterpriseSearchService:
    """End-to-end implementation of the target enterprise search/RAG pipeline."""

    def __init__(
        self,
        documents: Iterable[Document],
        events: Iterable[ActivityEvent] = (),
        *,
        now: datetime | None = None,
        query_understanding: QueryUnderstandingService | None = None,
        entitlement_service: EntitlementService | None = None,
        answer_service: GroundedAnswerService | None = None,
    ) -> None:
        docs = list(documents)
        self.now = now or datetime.utcnow()
        self.store = DocumentStore(docs)
        self.query_understanding = query_understanding or QueryUnderstandingService(now=self.now)
        self.entitlement = entitlement_service or EntitlementService()
        self.answer_service = answer_service or GroundedAnswerService()
        self.merger = CandidateMerger()
        self.ranker = MultiSignalRanker(now=self.now)
        self.indexes = {
            "vector": VectorIndex(docs),
            "bm25": BM25Index(docs),
            "metadata": MetadataIndex(docs),
            "title": TitleEntityIndex(docs),
            "recent": RecentActivityIndex(docs, events, now=self.now),
        }

    def search(self, query: str, user: UserContext, *, limit: int = 10, answer: bool = True) -> SearchResponse:
        started = perf_counter()
        sqo = self.query_understanding.understand(query)
        route_candidates: list[list[Candidate]] = []
        route_counts: dict[str, int] = {}
        for route in sqo.retrieval_plan:
            candidates = self.indexes[route].search(sqo, top_k=max(limit * 5, 20))
            route_counts[route] = len(candidates)
            route_candidates.append(candidates)
        merged = self.merger.merge(route_candidates)
        permissioned = [candidate for candidate in merged if self.entitlement.can_read(user, candidate.doc)]
        filtered = [candidate for candidate in permissioned if not candidate.doc.archived]
        ranked = self.ranker.rank(filtered, sqo, limit=limit)
        generated = self.answer_service.generate(sqo, ranked) if answer else self.answer_service.generate(sqo, [])
        results = tuple(self._to_result(candidate, sqo) for candidate in ranked)
        facets = self.indexes["metadata"].facets(candidate.doc for candidate in ranked)
        trace = {
            "route_counts": route_counts,
            "merged_candidates": len(merged),
            "permissioned_candidates": len(permissioned),
            "returned_results": len(results),
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "answer_confidence": generated.confidence,
            "no_answer": generated.no_answer,
        }
        return SearchResponse(query=sqo, answer=generated, results=results, facets=facets, trace=trace)

    @staticmethod
    def _to_result(candidate: Candidate, sqo) -> SearchResult:
        snippet = GroundedAnswerService._snippet(sqo, candidate.doc.body, max_chars=180)
        return SearchResult(
            doc_id=candidate.doc.doc_id,
            title=candidate.doc.title,
            url=candidate.doc.url,
            source=candidate.doc.source,
            score=round(candidate.score, 4),
            snippet=snippet,
            updated_at=candidate.doc.updated_at,
            explanation=tuple(candidate.explanation),
        )
