# Enterprise Search and RAG Target Architecture

## 1. Target architecture diagram

```text
                         ┌────────────────────────────────────────────┐
                         │ Enterprise Identity / SSO / Groups / OBO   │
                         └──────────────────────┬─────────────────────┘
                                                │
                                                ▼
┌──────────────┐   ┌───────────────────────────────────────────────────────────────┐
│ User / UI    │──▶│ Search API / Orchestrator                                    │
│ Search + RAG │   │ - Auth context, request budget, experiment assignment         │
└──────┬───────┘   │ - Query understanding, retrieval fanout, ranking, answering   │
       ▲           └──────────────┬────────────────────────────────────────────────┘
       │                          │
       │                          ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ Query Understanding Service                                  │
       │           │ intent, entities, aliases, freshness, source, filters, SQO    │
       │           └──────────────┬────────────────────────────────────────────────┘
       │                          │
       │                          ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ Retrieval Fanout                                             │
       │           │ vector + BM25 + metadata + title/entity + recent activity    │
       │           └──────┬─────────┬─────────┬──────────┬──────────┬─────────────┘
       │                  │         │         │          │          │
       │                  ▼         ▼         ▼          ▼          ▼
       │           ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
       │           │ Vector   │ │ BM25   │ │Metadata│ │Title / │ │ Recent       │
       │           │ Index    │ │ Index  │ │ Index  │ │Entity  │ │ Activity     │
       │           └────┬─────┘ └───┬────┘ └───┬────┘ │ Index  │ │ Index        │
       │                │           │          │      └───┬────┘ └──────┬───────┘
       │                └───────────┴──────────┴──────────┴─────────────┘
       │                                       │
       │                                       ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ ACL / Entitlement Filter                                     │
       │           │ pre-filter where possible; mandatory post-filter everywhere   │
       │           └──────────────┬────────────────────────────────────────────────┘
       │                          ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ Candidate Merge, Dedup, Parent Grouping, Feature Enrichment   │
       │           └──────────────┬────────────────────────────────────────────────┘
       │                          ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ Multi-Signal Ranker                                          │
       │           │ L1 fusion + business rules + L2 cross-encoder + diversification│
       │           └──────────────┬────────────────────────────────────────────────┘
       │                          ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ Grounded Answer Service                                      │
       │           │ evidence selection, prompt policy, citations, no-answer gate │
       │           └──────────────┬────────────────────────────────────────────────┘
       │                          ▼
       │           ┌───────────────────────────────────────────────────────────────┐
       │           │ Response Composer                                            │
       │           │ answer, citations, result cards, filters, explain snippets   │
       │           └──────────────┬────────────────────────────────────────────────┘
       │                          │
       └──────────────────────────┘

Ingestion side:

┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ Connectors   │─▶│ Normalizer   │─▶│ Chunk / Entity / │─▶│ Index Writers         │
│ SP, Conf,    │  │ canonical doc│  │ Metadata Extract │  │ vector, BM25, metadata│
│ Slack, ADO,  │  │ schema       │  │ embeddings, ACLs │  │ title, activity, ACL  │
│ GitHub, Mail │  └──────────────┘  └──────────────────┘  └──────────────────────┘
└──────────────┘          │                   │                       │
                          ▼                   ▼                       ▼
                   Raw content store   Knowledge graph / aliases   Telemetry lake
```

## 2. Major components and responsibilities

- **Source connectors** crawl or subscribe to SharePoint, Confluence, Slack public channels, Azure DevOps, GitHub, Outlook, and other systems. They must capture content, metadata, source permissions, update/delete events, and stable source identifiers.
- **Canonical document store** keeps normalized source records, chunk boundaries, raw text, rendered text, attachments, parent-child relationships, and version history. It is the replayable source of truth for re-indexing.
- **Metadata and entity extraction pipeline** normalizes authors, teams, departments, source names, dates, document types, tags, URLs, archived state, repository/project names, and aliases. It also detects entities such as system names, dashboards, services, acronyms, incident IDs, and teams.
- **Embedding service** creates query and document/chunk embeddings with versioned models. Embedding version must be stored so the platform can run dual indexes during migrations.
- **Index writers** update the vector index, keyword/BM25 index, metadata index, title/entity/alias index, recent activity index, and ACL store from the same canonical event stream.
- **Search API/orchestrator** owns authentication, request budgeting, fanout, timeout policy, ranking stages, answer generation, and response composition.
- **Query understanding service** converts a user query and user context into a structured query object with intent, entities, expansions, filters, freshness hints, and source preferences.
- **Retrieval services** generate candidates from semantic, lexical, structured, exact-match, and temporal routes. Each route returns normalized candidate IDs, route scores, snippets, and match evidence.
- **Entitlement service** evaluates whether the requesting principal can see each document/chunk using user ID, group IDs, OBO token claims, source ACLs, public-channel flags, inherited permissions, and deny rules.
- **Feature enrichment service** attaches freshness, popularity, source authority, ownership, activity, title-match, entity-match, ACL confidence, source-specific, and personalization features to candidates.
- **Ranker** performs multi-signal fusion, rule-based boosts/filters, cross-encoder reranking, optional learning-to-rank scoring, and source/result diversification.
- **Grounded answer service** selects evidence, asks the LLM to answer only from retrieved evidence, emits citations, and returns no-answer when evidence is weak or permissions are uncertain.
- **Observability and evaluation platform** records traces, retrieval sets, scores, permission decisions, citations, latency, token cost, click/feedback events, and offline benchmark metrics.

## 3. Retrieval flow from query to final answer

1. **Authenticate and authorize the request.** Resolve user ID, tenant, groups, role claims, source tokens, and request policy. Create a permission context for all downstream services.
2. **Understand the query.** Produce a structured query object containing intent, normalized text, entities, acronyms, source hints, time windows, metadata filters, freshness requirement, and retrieval plan.
3. **Run retrieval fanout in parallel.** Query vector, BM25, metadata, title/entity, and recent activity indexes with per-route top-k and latency budgets.
4. **Apply permission filtering.** Prefer pre-filtering by ACL bitsets or group allowlists in each index. Always perform mandatory post-filtering through the entitlement service before ranking and answering.
5. **Merge candidates.** Canonicalize IDs, combine chunk and document candidates, remove duplicates, keep route provenance, and group chunks by parent document.
6. **Enrich features.** Add source authority, freshness, popularity, title/entity match, exact phrase match, update recency, author/team affinity, and source-specific quality features.
7. **Rank in stages.** Run fast L1 fusion over hundreds or thousands of candidates, then cross-encoder rerank the top candidates, then apply final business rules such as archived demotion and diversity caps.
8. **Select evidence.** Choose top passages across distinct parent documents, preserving enough context for the LLM and citation spans.
9. **Generate grounded answer.** The LLM receives only permission-filtered evidence and must cite every substantive claim. If evidence coverage or confidence is weak, it returns a no-answer plus the best search results.
10. **Compose response.** Return answer, citations, result cards, source filters, metadata facets, recency labels, and optional explanation snippets.
11. **Log telemetry.** Store request trace, query object, candidates, scores, entitlement decisions, generation prompt metadata, citations, latency, cost, clicks, and feedback.

## 4. Indexes and tables needed

### Vector index

- **Purpose:** semantic retrieval over chunks and optionally parent document summaries.
- **Keys:** `chunk_id`, `doc_id`, `source_doc_id`, `embedding_version`.
- **Fields:** embedding vector, chunk text pointer, title, source, doc type, updated_at, language, archived flag, ACL pre-filter fields, parent doc pointer.
- **Filters:** source, doc_type, business_unit, department, owner_team, date ranges, archived, visibility class, tenant.
- **Operational notes:** run separate namespaces by embedding version, use approximate nearest neighbor search, keep tombstone/delete propagation under an explicit SLA.

### Keyword/BM25 index

- **Purpose:** lexical recall, acronym matching, code names, incident IDs, exact phrases, repository names, and rare terms.
- **Fields:** title, body/chunk text, headings, comments, tags, source-specific fields, normalized tokens, shingles, synonyms.
- **Scoring:** BM25 plus field boosts: title > headings > tags > body > comments.
- **Operational notes:** support phrase queries, term proximity, spelling correction, stemming controls, and source-aware analyzers for code, Slack, tickets, and mail.

### Metadata index

- **Purpose:** structured filtering and faceting over source, author, owner team, business unit, department, dates, doc type, tags, URL, archived state, and source-specific fields.
- **Schema examples:** `source`, `title.keyword`, `author_id`, `owner_team_id`, `business_unit`, `department`, `created_at`, `updated_at`, `doc_type`, `tags`, `url`, `archived`, `repo`, `project`, `channel`, `space`, `site`.
- **Operational notes:** use normalized IDs for people/teams and keep display labels separately to survive renames.

### Title/entity/alias index

- **Purpose:** exact and near-exact lookup for document titles, dashboards, services, teams, project names, acronyms, repositories, and known enterprise entities.
- **Data:** canonical entity ID, aliases, abbreviations, title variants, owner, entity type, popularity, source authority, URL, related docs.
- **Matching:** exact normalized match, prefix match, acronym expansion, alias expansion, fuzzy match with conservative thresholds, and entity disambiguation.
- **Operational notes:** this index should be small and fast enough to query for every request.

### Recent activity index

- **Purpose:** serve freshness-oriented queries and activity feeds.
- **Events:** created, updated, commented, mentioned, merged, closed, viewed, clicked, shared, reacted, incident updated.
- **Fields:** `event_id`, `doc_id`, `chunk_id`, `actor_id`, `source`, `event_type`, `event_time`, `activity_text`, `visibility`, `acl_snapshot_id`.
- **Operational notes:** store event-level ACL or document ACL snapshot to avoid leaking private activity names.

### ACL/entitlement store

- **Purpose:** low-latency permission checks and auditable authorization decisions.
- **Data:** document ACLs, inherited ACLs, source visibility, user/group allow and deny entries, source-specific permission model, ACL version, last validated time.
- **Patterns:** precomputed group bitsets for common indexes, dynamic OBO validation for high-risk sources, cached decisions with short TTL, and fail-closed behavior.

## 5. Query understanding design

The query understanding service should emit a **structured query object (SQO)**:

```json
{
  "raw_query": "latest claims FNOL process",
  "normalized_query": "claims first notice of loss process",
  "intent": "fresh_process_lookup",
  "entities": [
    {"text": "FNOL", "canonical": "First Notice of Loss", "type": "acronym", "confidence": 0.92},
    {"text": "claims", "type": "business_domain", "confidence": 0.86}
  ],
  "expanded_terms": ["first notice of loss", "FNOL", "claims intake"],
  "filters": {"archived": false},
  "time_window": {"field": "updated_at", "gte": "now-180d"},
  "source_preferences": ["Confluence", "SharePoint"],
  "retrieval_plan": ["title_entity", "bm25", "vector", "metadata"],
  "answer_policy": {"require_citations": true, "allow_no_answer": true}
}
```

- **Intent detection:** classify queries into known-item lookup, how-to/process, troubleshooting, recent activity, people/team ownership, code/repository, ticket/work-item, dashboard/report, broad discovery, and answer-seeking RAG.
- **Acronym/entity expansion:** resolve enterprise acronyms such as ABS, FNOL, IRS, and ADO against an alias graph. Keep multiple candidates when ambiguous and let retrieval/ranking disambiguate with user department, source, and popularity.
- **Freshness detection:** detect terms such as latest, recent, last week, current, new, updated, incident, status, and roadmap. Convert relative dates into absolute windows at request time.
- **Source preference:** infer source hints from query terms, for example repo/code implies GitHub, ticket/story/bug implies ADO, channel/thread implies Slack, dashboard implies BI/SharePoint/Confluence, process/policy implies SharePoint or Confluence.
- **Structured query object:** use one typed object across retrieval, ranking, answer generation, logging, and evaluation so behavior can be replayed and debugged.

## 6. Ranking design

Use a staged ranking architecture rather than one monolithic model.

### L0: hard constraints

- Tenant, user permission, legal hold, archived inclusion policy, source availability, and explicit user filters are hard constraints.
- ACL filtering is not a ranking signal; it is a mandatory visibility gate. ACL confidence can be a diagnostic feature, but uncertain permissions must fail closed.

### L1: candidate fusion and feature scoring

A practical initial scoring formula:

```text
score_l1 =
  0.30 * dense_score_norm +
  0.25 * keyword_score_norm +
  0.15 * title_entity_score +
  0.10 * freshness_score +
  0.08 * source_authority_score +
  0.07 * popularity_score +
  0.05 * metadata_match_score
```

Weights should be query-intent dependent. Known-item queries should boost title/entity and exact phrase. Troubleshooting queries should boost BM25, recency, and source activity. Process queries should boost source authority and freshness.

### L2: cross-encoder reranking

- Rerank the top 50-200 chunks or parent snippets with a cross-encoder using query, title, snippet, source, updated_at, and headings.
- Use route-aware sampling so exact title hits are not lost before cross-encoder reranking.
- Keep cross-encoder features logged for offline analysis and distillation.

### Final ranking rules

- Demote archived documents unless explicitly requested.
- Prefer authoritative sources for policies/processes.
- Diversify by parent document and source when the query is exploratory.
- Do not diversify known-item searches too aggressively; exact matches should appear first.
- Boost documents owned by the user's team only as a soft personalization signal, never as a permission substitute.

## 7. How metadata search should work

Metadata search should be a first-class retrieval route and a filter/facet layer, not just a vector DB filter. The system should parse structured hints from natural language and explicit UI filters into the SQO. Examples include `source:Confluence`, `owner_team:Claims`, `updated_after:2026-01-01`, `doc_type:runbook`, `department:Engineering`, `archived:false`, `repo:payments-service`, or `channel:#milvus-support`.

Implementation guidance:

- Normalize every metadata value to stable IDs and keep display labels for UI rendering.
- Support exact, prefix, and controlled fuzzy matching on metadata values.
- Expose facets for source, owner team, doc type, department, updated date, and tags.
- Use metadata matches as both hard filters and soft ranking boosts depending on query confidence.
- Keep metadata-only retrieval for queries such as `claims docs updated last month` or `ADO bugs owned by platform`.
- Treat archived and permission constraints as hard filters unless the user explicitly changes the archived filter and is authorized to view the content.

## 8. How exact title/entity search should work

Exact title/entity search handles known-item queries that dense retrieval often misses. It should run for every query with high priority and low latency.

Recommended matching pipeline:

1. Normalize query and titles: lowercase, trim punctuation, collapse whitespace, remove stopword-only suffixes, normalize Unicode, expand common abbreviations.
2. Generate candidates from exact title, exact alias, prefix title, acronym expansion, keyword title BM25, and conservative fuzzy matching.
3. Disambiguate using entity type, source authority, popularity, owner team, freshness, user context, and query intent.
4. Return entity cards when the entity itself is the answer, and related documents when the entity maps to multiple artifacts.
5. Preserve the exact-match route as a feature so ranking can avoid burying known-item results.

Examples:

- `IRS dashboard` may mean an internal dashboard, not the tax agency. The alias/entity index should resolve IRS to internal dashboard candidates and use user department and prior clicks to disambiguate.
- `Temporal scaling guide` should match the exact or near-exact document title even if the body text uses terms such as workflow engine, workers, namespaces, and task queues.

## 9. How recent activity search should work

Recent activity search should combine event retrieval with document retrieval. The activity index answers questions about what changed, while the document indexes answer the current state.

Design:

- Convert freshness phrases into absolute windows, for example `last week` means the previous calendar week in the user's timezone unless the product chooses rolling seven days.
- Query the activity index for event text, actor, source, entity, event type, and time window.
- Join activity events to current permission-filtered documents.
- Rank by time decay, event importance, source relevance, actor/team relevance, and text match.
- Surface both the activity event and the current document state, clearly labeling whether the cited evidence is an event, a comment, a ticket, or the current document.

Example: `Milvus latency issue last week` should query Slack, ADO, incident docs, GitHub issues/PRs, and runbooks for Milvus plus latency terms within the last-week window, then group results by incident/ticket/thread when possible.

## 10. How permission filtering should work

Permission filtering must be designed as a security boundary, not a UX feature.

- **Identity resolution:** derive user ID, tenant, groups, roles, and source tokens from SSO and OBO context.
- **ACL ingestion:** capture source-specific ACLs, inheritance, public/private flags, channel membership, repository visibility, mail recipient restrictions, and explicit deny entries.
- **Pre-filtering:** push ACL constraints into vector, BM25, metadata, and activity indexes using visibility classes, tenant IDs, group bitsets, and source-specific allowlists.
- **Post-filtering:** call the entitlement service on every candidate that survives retrieval before ranking, snippets, or LLM context.
- **Source validation:** for high-risk or frequently changing permissions, optionally validate with the source API using OBO tokens.
- **Cache policy:** cache user group memberships and ACL decisions with short TTLs and ACL-version keys. Invalidate on permission changes.
- **Fail-closed:** if ACL metadata is missing, stale beyond SLA, contradictory, or source validation fails, suppress the result and log a security diagnostic.
- **Generation safety:** never put unauthorized snippets, titles, URLs, or metadata into the LLM prompt or logs visible to users.

## 11. Deduplication and parent-document grouping

Deduplication should happen at multiple levels:

- **Canonical ID dedup:** merge the same chunk or document returned by multiple retrieval routes.
- **Version dedup:** collapse older versions and drafts behind the latest authoritative version unless the query asks for history.
- **Near-duplicate dedup:** use content hashes, SimHash/MinHash, source URL canonicalization, and title similarity to group replicated docs.
- **Chunk grouping:** group chunks under parent documents for UI cards and LLM evidence selection.
- **Thread grouping:** group Slack messages by thread and ADO/GitHub comments by work item, issue, or PR.
- **Attachment grouping:** attach PDFs, slides, and spreadsheets to the parent page or message when appropriate.

For ranking, score chunks first but present parent documents. Parent score can be computed from the best chunk, number of strong chunks, title match, source authority, freshness, and diversity constraints.

## 12. LLM answer generation layer

The LLM layer should be a grounded synthesis service, not an open-ended chat layer.

- **Evidence input:** pass only permission-filtered chunks, titles, source names, URLs, dates, and citation IDs.
- **Evidence selection:** use top-ranked diverse snippets, favor authoritative and recent sources, and include metadata needed to judge freshness.
- **Prompt policy:** instruct the model to answer only from evidence, cite each key claim, identify uncertainty, and avoid using prior knowledge for enterprise facts.
- **No-answer behavior:** return a clear no-answer when retrieved evidence is insufficient, contradictory, unauthorized, or stale for a freshness-sensitive query.
- **Citation format:** citations should point to source documents and, where possible, exact sections, headings, timestamps, comments, or line anchors.
- **Grounding checks:** before returning, verify every citation ID exists in the evidence pack and that answer claims have supporting evidence.
- **Response shape:** provide a concise direct answer, cited supporting bullets, source/result cards, and suggested refinements or filters.
- **Cost controls:** use smaller models for query understanding and evidence compression, reserve larger models for answer synthesis, and cache deterministic intermediate outputs.

## 13. Evaluation strategy

- **Recall:** build route-level and blended recall sets for known-item, troubleshooting, process, dashboard, code, ticket, people/team, and recent-activity queries. Measure recall@50, recall@100, and recall before/after ACL filtering.
- **Precision:** use judged top results and click satisfaction labels to measure precision@5 and precision@10.
- **MRR/NDCG:** measure known-item MRR and graded NDCG@10 for multi-result queries. Segment by source, department, query intent, and freshness.
- **Citation correctness:** evaluate whether cited documents support each answer claim, whether citations are permission-safe, and whether cited snippets are the minimal relevant evidence.
- **Permission correctness:** run synthetic users and groups against seeded documents with allow, deny, inherited, private, and stale ACL cases. Track false allow as severity-zero incidents.
- **Freshness:** measure whether fresh-intent queries return documents or events within expected time windows and whether stale authoritative content is labeled correctly.
- **Latency:** track p50, p95, and p99 for query understanding, each retrieval route, ACL filtering, ranking, cross-encoder, LLM generation, and total time to first token.
- **Online evaluation:** use interleaving or guarded A/B tests for ranking changes, with click success, reformulation rate, answer helpfulness, and no-result rate.
- **Human review:** maintain an evaluation console where SMEs judge relevance, freshness, citations, and missing results.

## 14. Observability dashboards and logs needed

Dashboards:

- **Search health:** query volume, success rate, no-result rate, no-answer rate, timeout rate, source/index freshness, ingestion lag, delete lag.
- **Latency:** end-to-end and per-component p50/p95/p99, fanout timeouts, cross-encoder queue time, LLM time to first token and total generation time.
- **Quality:** recall benchmark trends, NDCG/MRR, click-through, long-click, reformulation rate, filter usage, abandonment, answer helpfulness.
- **Security:** permission denials, missing ACLs, stale ACLs, fail-closed counts, source validation failures, unauthorized-access test results.
- **Cost:** embedding cost, indexing cost, vector query cost, cross-encoder GPU cost, LLM token cost, cache hit rate, cost per successful search.
- **Source coverage:** documents indexed by source, errors by connector, tombstones processed, activity events indexed, metadata completeness.

Logs and traces:

- Request ID, user/tenant hash, query hash, SQO, experiment arm, retrieval plan, route top-k, timeouts.
- Candidate IDs, route scores, normalized features, ACL decision, dedup group, final rank, cross-encoder score.
- Evidence pack IDs, prompt template version, model version, token counts, answer confidence, citation IDs, no-answer reason.
- Clicks, dwell, copy, open-source, thumbs feedback, explicit report issue, and subsequent reformulations.

## 15. Phased roadmap

### Phase 1: must-have Glean parity

- Add BM25/keyword retrieval alongside vector retrieval.
- Add metadata index and UI facets for source, owner team, doc type, updated date, tags, and archived status.
- Add title/entity/alias index for known-item lookup.
- Add mandatory entitlement service and post-retrieval ACL filtering.
- Add candidate merge, deduplication, and parent-document grouping.
- Add basic multi-signal ranking with dense, BM25, title, freshness, source authority, and popularity features.
- Add grounded answer generation with citations and no-answer behavior.
- Establish baseline evaluation sets, permission test suite, and latency/cost dashboards.

### Phase 2: better ranking and personalization

- Improve query understanding with intent detection, acronym expansion, source preference, and freshness windows.
- Add recent activity index and route for incidents, comments, tickets, PRs, Slack threads, and document updates.
- Add source-specific ranking features and authority maps for policies, runbooks, code, dashboards, and tickets.
- Add soft personalization by team, role, geography, recency of user interactions, and subscribed sources.
- Add answer grounding verifier and citation quality evaluator.
- Add online experimentation and interleaving for ranker changes.

### Phase 3: advanced learning-to-rank and feedback loop

- Train learning-to-rank models from judged data, clicks, long-clicks, reformulations, and explicit feedback.
- Distill cross-encoder scores into cheaper rankers for lower latency.
- Add active learning workflows for low-confidence queries and high-volume failed searches.
- Add query/session understanding, task-aware search, and proactive recommendations.
- Add knowledge graph expansion for entities, owners, systems, dependencies, dashboards, repositories, and incidents.
- Add automated quality gates for every indexing, ranking, embedding, and prompt change.

## 16. Risks, tradeoffs, and open questions

Risks and tradeoffs:

- **Security versus latency:** strict ACL checks add latency. Use pre-filtering for scale but keep mandatory post-filtering for safety.
- **Freshness versus stability:** fresh activity can dominate authoritative docs. Make freshness intent-aware and label event evidence clearly.
- **Personalization versus neutrality:** personalization can help users but may hide globally authoritative content. Keep personalization soft and explainable.
- **Recall versus cost:** broad fanout improves recall but raises query cost. Use intent-based retrieval plans, budgets, and adaptive top-k.
- **Cross-encoder quality versus latency:** cross-encoders improve precision but can become the bottleneck. Rerank a bounded set and consider distillation.
- **Alias expansion versus ambiguity:** acronyms such as ABS and IRS can mean many things. Preserve ambiguity early and disambiguate during ranking.
- **LLM confidence versus user trust:** a fluent answer with weak evidence is worse than a no-answer. Enforce evidence coverage and citation checks.
- **Connector correctness:** source APIs differ in permission, deletion, and version semantics. Validate each connector with source-specific conformance tests.

Open questions:

- Which sources are authoritative for policy, process, engineering runbooks, dashboards, incidents, and ownership?
- What are the freshness SLAs for each source and for permission propagation?
- Should `last week` mean previous calendar week or rolling seven days for enterprise users?
- Which metadata fields are guaranteed across all sources, and which are source-specific?
- What is the required p95 latency for search results and for generated answers?
- Which user interactions can legally and ethically feed personalization and learning-to-rank?
- How should private Outlook content participate in enterprise RAG, if at all?
- What is the escalation path for false permission allows, stale answers, and incorrect citations?

## Concrete query examples

### `ABS onboarding`

- **Likely intent:** known-item or process lookup.
- **Query understanding:** expand ABS through alias graph; preserve multiple meanings if ambiguous.
- **Retrieval:** title/entity index for `ABS`, BM25 for exact acronym and onboarding, vector for semantic onboarding content, metadata filters for non-archived process docs.
- **Ranking:** boost exact title/entity matches and authoritative onboarding docs, demote stale or archived pages.
- **Answer:** summarize the onboarding steps only if evidence includes current onboarding documentation with citations.

### `Milvus latency issue last week`

- **Likely intent:** recent troubleshooting or incident lookup.
- **Query understanding:** entity `Milvus`, issue type `latency`, time window `last week`.
- **Retrieval:** recent activity index for Slack/ADO/GitHub/incident events, BM25 for exact terms, vector for related runbooks and incident summaries.
- **Ranking:** boost recent events, incidents, tickets, and threads; group by incident/thread/work item.
- **Answer:** report what happened and current status only from cited incident/ticket/thread evidence; otherwise return search results and state that no authoritative summary was found.

### `latest claims FNOL process`

- **Likely intent:** fresh process lookup.
- **Query understanding:** expand FNOL to First Notice of Loss, infer Claims domain, require recent/current docs.
- **Retrieval:** title/entity, BM25, vector, and metadata filters for process/policy docs owned by Claims.
- **Ranking:** boost updated authoritative Confluence/SharePoint process docs and demote older duplicates.
- **Answer:** cite the latest process page and include updated date; no-answer if only stale or contradictory docs are available.

### `Temporal scaling guide`

- **Likely intent:** exact document lookup or engineering guide.
- **Query understanding:** entity `Temporal`, title phrase `scaling guide`, source preference Confluence/GitHub.
- **Retrieval:** title exact/prefix, BM25 title fields, vector for semantic scaling content.
- **Ranking:** boost exact title match and current engineering-owned guide; group duplicate chunks under the parent doc.
- **Answer:** show the guide as the top result and optionally summarize scaling recommendations from cited sections.

### `IRS dashboard`

- **Likely intent:** dashboard known-item lookup.
- **Query understanding:** resolve IRS against internal aliases and dashboard entities; avoid assuming public tax-agency meaning.
- **Retrieval:** title/entity/alias index, metadata for doc_type dashboard/report, BM25 title fields.
- **Ranking:** boost dashboard/report entities, source authority for BI catalogs, popularity, and user's department affinity.
- **Answer:** return the dashboard card with URL and owner if permission allows; if multiple IRS dashboards exist, ask a disambiguating refinement or show grouped candidates.
