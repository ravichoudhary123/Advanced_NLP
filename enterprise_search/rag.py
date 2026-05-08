"""Grounded answer generation layer."""
from __future__ import annotations

from .indexes import tokenize
from .models import Answer, Candidate, Citation, StructuredQuery


class GroundedAnswerService:
    """Generates extractive, citation-backed answers with no-answer behavior."""

    def __init__(self, min_confidence: float = 0.28, max_citations: int = 3) -> None:
        self.min_confidence = min_confidence
        self.max_citations = max_citations

    def generate(self, sqo: StructuredQuery, ranked: list[Candidate]) -> Answer:
        evidence = [candidate for candidate in ranked if candidate.score > 0][: self.max_citations]
        confidence = self._confidence(sqo, evidence)
        citations = tuple(
            Citation(doc_id=item.doc.doc_id, title=item.doc.title, url=item.doc.url, source=item.doc.source) for item in evidence
        )
        if not evidence or confidence < self.min_confidence:
            return Answer(
                text="I could not find enough permissioned, relevant evidence to answer this confidently.",
                citations=citations,
                confidence=confidence,
                no_answer=True,
            )
        bullets = []
        for item in evidence:
            snippet = self._snippet(sqo, item.doc.body)
            bullets.append(f"- {snippet} [{item.doc.title}]")
        return Answer(
            text="Based on the permissioned enterprise sources I found:\n" + "\n".join(bullets),
            citations=citations,
            confidence=confidence,
            no_answer=False,
        )

    @staticmethod
    def _confidence(sqo: StructuredQuery, evidence: list[Candidate]) -> float:
        if not evidence:
            return 0.0
        query_terms = set(tokenize(sqo.normalized_query or sqo.raw_query))
        coverage = 0.0
        for item in evidence:
            doc_terms = set(tokenize(f"{item.doc.title} {item.doc.body}"))
            coverage = max(coverage, len(query_terms.intersection(doc_terms)) / max(len(query_terms), 1))
        score_component = min(max(evidence[0].score / 8.0, 0.0), 1.0)
        return round(coverage * 0.65 + score_component * 0.35, 3)

    @staticmethod
    def _snippet(sqo: StructuredQuery, body: str, max_chars: int = 220) -> str:
        terms = set(tokenize(sqo.normalized_query or sqo.raw_query))
        sentences = [part.strip() for part in body.replace("\n", " ").split(".") if part.strip()]
        if not sentences:
            return body[:max_chars]
        best = max(sentences, key=lambda sentence: len(terms.intersection(tokenize(sentence))))
        return (best[: max_chars - 1] + "…") if len(best) > max_chars else best
