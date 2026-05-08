# Enterprise Search/RAG Reference Implementation

This repository includes a small, dependency-free Python implementation of the
enterprise search architecture described in `docs/enterprise_search_rag_architecture.md`.
It is intended as an executable platform blueprint rather than a production search
cluster.

## What is implemented

- `EnterpriseSearchService` orchestrates query understanding, retrieval fanout,
  permission filtering, merge/deduplication, ranking, grounded answer generation,
  facets, and trace metadata.
- `QueryUnderstandingService` emits a structured query object with intent,
  normalized text, acronym expansion, source preference, metadata filters,
  freshness windows, and retrieval plan.
- Retrieval indexes include in-memory vector-style sparse cosine search, BM25,
  metadata filtering/faceting, title/entity/alias lookup, and recent activity.
- `EntitlementService` applies a mandatory fail-closed post-filter using tenant,
  user, group, allow, and deny ACL metadata.
- `MultiSignalRanker` combines dense, keyword, title/entity, metadata, freshness,
  source authority, popularity, and cross-encoder-style lexical interaction
  features.
- `GroundedAnswerService` builds citation-backed extractive answers and returns a
  no-answer response when evidence confidence is weak.

## Minimal usage

```python
from datetime import datetime
from enterprise_search import ACL, Document, EnterpriseSearchService, UserContext

now = datetime.utcnow()
docs = [
    Document(
        doc_id="temporal-scaling",
        title="Temporal Scaling Guide",
        body="Scale Temporal workers by separating task queues and tracking poller saturation.",
        source="confluence",
        url="https://example.test/temporal-scaling",
        acl=ACL(allow_groups=frozenset({"engineering"})),
        updated_at=now,
        aliases=("Temporal scaling guide",),
    )
]

service = EnterpriseSearchService(docs, now=now)
response = service.search("Temporal scaling guide", UserContext("u123", frozenset({"engineering"})))
print(response.results[0].title)
print(response.answer.text)
```

## Production replacement points

The classes are intentionally small and composable so a platform team can replace
one layer at a time:

1. Replace in-memory indexes with OpenSearch/Elasticsearch, a vector database,
   entity service, and event store adapters while preserving the `search(sqo)`
   contract.
2. Replace the rule-based query understanding service with a classifier/LLM that
   emits the same structured query object.
3. Replace the heuristic ranker with a learned LTR model and keep the current
   features as baseline features.
4. Replace the extractive answer service with an LLM call that receives only
   permission-filtered evidence and enforces citation/no-answer policy.
5. Stream trace metadata into the enterprise observability stack for latency,
   recall, permission correctness, citation correctness, and cost dashboards.
