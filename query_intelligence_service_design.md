# Query Intelligence Service (Enterprise Search) — Production Implementation Design

This design assumes:
- **Stack:** Python/FastAPI (or Java/Spring Boot), Redis, Postgres, optional OpenSearch, Kafka/Kinesis + batch jobs.
- **Placement:** Query Intelligence is called **before** lexical/semantic retrieval.
- **Constraints:** Multi-tenant isolation, low-latency, no leakage of sensitive query patterns, useful in cold start, deterministic first.

---

## Capability 1: Autocomplete

### A) Purpose
- Solves incomplete query entry by predicting likely full queries/entities while user types.
- Belongs in Query Intelligence because it is a **UI-time assist + prefix retrieval problem**, not document retrieval. Semantic search should receive the improved query, not generate keystroke-time candidates.

### B) Inputs and outputs
**Endpoint:** `POST /v1/query-intelligence/autocomplete`

**Request JSON**
```json
{
  "tenant_id": "t_acme",
  "user_id": "u_123",
  "session_id": "s_abc",
  "prefix": "annu",
  "locale": "en-US",
  "limit": 8,
  "context": {
    "department": "finance",
    "app_surface": "global_search",
    "acl_tags": ["finance", "public"]
  }
}
```

**Response JSON**
```json
{
  "request_id": "req_1",
  "candidates": [
    {
      "text": "annual budget 2025",
      "type": "query",
      "score": 0.92,
      "reasons": ["prefix_match", "tenant_popular", "recent_trend"]
    },
    {
      "text": "annual report template",
      "type": "doc_title",
      "score": 0.87,
      "reasons": ["prefix_match", "taxonomy_term"]
    }
  ],
  "latency_ms": 12
}
```

**Latency target**
- p50 < 15 ms, p95 < 40 ms, hard timeout 60 ms.

### C) Core algorithm / logic
1. Normalize prefix (`NFKC`, lowercase, trim, collapse whitespace).
2. Reject if length `< 2` (return empty or fallback static terms).
3. Query **tenant-scoped prefix index** (Redis trie/FST or in-memory FST shard) for top N raw matches.
4. Merge candidate pools:
   - historical query prefixes,
   - controlled vocabulary terms,
   - high-frequency document titles/tags/headings.
5. Filter candidates:
   - blocked terms list,
   - PII/sensitive regex + classifier,
   - ACL incompatibility.
6. Score each candidate:
   - `score = 0.45*prefix_score + 0.25*tenant_pop + 0.10*recency + 0.10*user_affinity + 0.10*quality`.
7. Diversify (max 2 near-duplicates by token Jaccard > 0.9).
8. Return top `limit`.

**Matching details**
- Prefix match on token boundaries and full string prefix.
- Tokenization: language-aware (ICU), preserve enterprise tokens (`SLA-2`, `QBR`, `FY25`).

### D) Data model
**Primary online stores**
- Redis: hot prefix->candidate IDs, per-tenant sorted sets.
- Optional memory-mapped FST per tenant for ultra-low-latency prefix expansion.
- Postgres: source-of-truth candidate table + metadata.

**Schema (Postgres)**
- `qi_autocomplete_candidates`
  - `tenant_id`, `candidate_id`, `text`, `normalized_text`, `source_type` (`query|taxonomy|title|tag`), `popularity_7d`, `popularity_30d`, `last_seen_at`, `quality_score`, `is_blocked`.
- index: `(tenant_id, normalized_text text_pattern_ops)`.

**Partitioning**
- Partition by `tenant_id_hash` for both Postgres table partitions and Redis key prefixes: `qi:{tenant}:{feature}:...`.

### E) Data sources
- Query logs (typed prefix and submitted query).
- Click logs for accepted suggestions.
- Document metadata (titles/headings/tags).
- Enterprise taxonomy/glossary.
- Synonyms/acronyms dictionary (`SOW` -> `statement of work`).

### F) Ranking strategy
- Prioritize exact prefix + tenant popularity.
- Add recency trend boost (e.g., exponential decay half-life 14 days).
- Personalization only as tie-breaker (avoid overfitting to one user).
- Downrank noisy items: low CTR, high abandonment, flagged unsafe.

### G) Online serving architecture
- API Gateway -> Query Intelligence `/autocomplete`.
- L1 in-process cache (1–5s TTL) for `(tenant,prefix,context-hash)`.
- L2 Redis cache (30–120s TTL) for hot prefixes.
- Fallback: if index unavailable, return taxonomy seeds + recent searches.
- Rate limit: per user 20 RPS burst, 5 RPS sustained.

### H) Offline pipelines
- Streaming job aggregates prefix frequencies hourly.
- Nightly rebuild of prefix index per tenant.
- Weekly quality pruning using CTR/skip metrics.
- Cold start: bootstrap from taxonomy + document titles.

### I) Multi-tenancy and access control
- Strict tenant-level index separation.
- Candidate generation from tenant-owned corpus only.
- ACL tag filtering (role/group) before returning candidates.
- Never use cross-tenant popularity.

### J) Evaluation
- Offline: MRR@k for accepted suggestion logs, prefix recall@k.
- Online: autocomplete CTR, suggestion acceptance, latency p95, cache hit ratio.
- A/B test ranking weights by tenant cohort.

### K) Failure modes / risks
- Prefix bias toward over-frequent terms.
- Sensitive term leakage from raw logs.
- Stale trends after org events.
- Mitigations: minimum support thresholds, safety filter, faster trend refresh.

### L) MVP vs roadmap
- **Now:** deterministic prefix retrieval + popularity + blocklist.
- **Later:** learned ranking model, contextual embeddings, multilingual morphology.

---

## Capability 2: Query Suggestions

### A) Purpose
- Suggests **alternative or next-step queries** when current query is weak/ambiguous.
- In Query Intelligence because it is query reformulation UX; semantic retrieval should consume chosen suggestion.

### B) Inputs and outputs
**Endpoint:** `POST /v1/query-intelligence/suggestions`

**Request**
```json
{
  "tenant_id": "t_acme",
  "user_id": "u_123",
  "query": "pto policy contractors",
  "limit": 6,
  "signals": {
    "recent_queries": ["leave policy", "contractor onboarding"],
    "zero_result_last_query": true
  }
}
```

**Response**
```json
{
  "candidates": [
    {
      "text": "paid time off policy for contractors",
      "type": "expansion",
      "score": 0.89,
      "reasons": ["synonym_expand", "high_click_followup"]
    },
    {
      "text": "contractor leave eligibility",
      "type": "related",
      "score": 0.75
    }
  ]
}
```

**Latency:** p95 < 80 ms (can be slightly higher than autocomplete).

### C) Core algorithm / logic
1. Normalize + tokenize query.
2. Generate candidates from:
   - synonym/abbreviation expansion,
   - co-click/co-session query graph,
   - taxonomy neighbors,
   - zero-result recovery templates.
3. Remove duplicates/near-duplicates.
4. Score:
   - lexical similarity to original,
   - historical success rate (CTR, dwell),
   - zero-result recovery probability,
   - personalization alignment.
5. Safety + ACL filtering.
6. Return top diversified list (intent variants).

### D) Data model
- `qi_query_graph_edges(tenant_id, q1, q2, edge_type, weight, updated_at)`.
- `qi_synonyms(tenant_id, term, expansions[], confidence, source)`.
- Redis adjacency cache: `qi:{tenant}:qgraph:{query_hash}` -> top neighbors.
- Optional OpenSearch index for semantic nearest historical queries (Phase 3).

### E) Data sources
- Session chains (`query -> next_query`).
- Query-to-clicked-document logs.
- Tenant taxonomy and controlled phrases.
- Zero-result events and successful reformulations.

### F) Ranking strategy
`score = 0.35*historical_success + 0.25*intent_similarity + 0.20*recovery_score + 0.10*recency + 0.10*user_affinity`
- Apply cap so personalized boost cannot reorder top 2 unless strong evidence.

### G) Online serving architecture
- `/suggestions` calls candidate generators in parallel with per-source 20 ms budget.
- Merge/rank within global timeout 90 ms.
- Cache by `(tenant, query_norm, context_segment)` for 60s.
- Fallback to synonym expansions only.

### H) Offline pipelines
- Build query reformulation graph daily + mini-batch hourly updates.
- Compute edge weights with decay and minimum support (`>=10` transitions).
- Refresh synonym dictionary from taxonomy pipeline weekly.

### I) Multi-tenancy and access control
- Query graph computed per tenant only.
- Optional department-level segments as separate overlays.
- ACL filtering for suggestions tied to restricted content concepts.

### J) Evaluation
- Suggestion acceptance rate.
- Zero-result rescue rate.
- Downstream search CTR uplift.
- Reformulation success within 2 hops.

### K) Failure modes / risks
- Query drift (suggestions change user intent).
- Suggestion loops (`A -> B -> A`).
- Noisy graph edges from bots.
- Mitigate with bot filtering + loop penalty.

### L) MVP vs roadmap
- **Now:** synonym + graph-neighbor deterministic suggestions.
- **Later:** small learning-to-rank model and semantic neighborhood mining.

---

## Capability 3: Recent Searches

### A) Purpose
- Re-surface a user’s own recent queries for convenience and task continuity.
- Belongs here because it is user history UX, not retrieval relevance.

### B) Inputs and outputs
**Endpoint:** `GET /v1/query-intelligence/recent?tenant_id=t_acme&user_id=u_123&limit=10`

**Response**
```json
{
  "recent": [
    {"text": "vendor risk policy", "last_used_at": "2026-04-05T10:10:00Z", "count": 3},
    {"text": "soc2 evidence checklist", "last_used_at": "2026-04-04T09:00:00Z", "count": 1}
  ]
}
```

**Latency:** p95 < 20 ms.

### C) Core algorithm / logic
1. Read user’s recent query list from Redis sorted set by timestamp.
2. Deduplicate by normalized query (keep latest timestamp + count).
3. Filter blocked/sensitive strings.
4. Return top `limit` descending by `last_used_at`.

### D) Data model
- Redis ZSET: `qi:{tenant}:recent:{user}` score=`unix_ts`, value=`query_norm`.
- Redis HASH: per query metadata (`display_text`, `count`).
- Postgres async sink for durability/audit.

### E) Data sources
- Search submit events only (not each keypress).
- Optional: include clicked suggestions as searches.

### F) Ranking strategy
- Pure recency first; secondary by frequency within recent window.
- Ignore old entries older than policy (e.g., 90 days).

### G) Online serving architecture
- write path async via event bus; read path direct Redis.
- On Redis miss, fallback to Postgres last 20 events.

### H) Offline pipelines
- Daily TTL cleanup + compaction.
- Privacy purge jobs for delete requests.

### I) Multi-tenancy and access control
- Key namespace includes tenant and user.
- Strictly user-private by default.
- Optional team-shared recents require explicit opt-in + ACL.

### J) Evaluation
- reuse rate of recent queries.
- impact on time-to-first-click.

### K) Failure modes / risks
- Storing sensitive queries too long.
- Cross-user leakage due to key bugs.
- Mitigation: strong key schema tests + encryption + short retention.

### L) MVP vs roadmap
- **Now:** per-user recents with TTL.
- **Later:** task-based grouping and pinned recents.

---

## Capability 4: Popular Searches

### A) Purpose
- Shows tenant-level trending/popular queries to guide discovery and cold-start users.
- Query Intelligence concern because this is query analytics surfacing, independent of retrieval.

### B) Inputs and outputs
**Endpoint:** `GET /v1/query-intelligence/popular?tenant_id=t_acme&window=7d&limit=10&segment=finance`

**Response**
```json
{
  "popular": [
    {"text": "expense policy", "score": 0.91, "trend": "+18%"},
    {"text": "q2 budget template", "score": 0.78, "trend": "+6%"}
  ],
  "window": "7d"
}
```

**Latency:** p95 < 25 ms.

### C) Core algorithm / logic
1. Fetch precomputed popular list for `(tenant, segment, window)`.
2. Score combines volume + success + trend:
   - `pop = log1p(search_count_7d)`
   - `success = ctr_7d * (1 - zero_result_rate)`
   - `trend = (count_1d / max(count_prev_7d_avg,1))`
   - final `0.5*pop + 0.3*success + 0.2*trend`.
3. Filter unsafe/noisy terms, min support threshold.

### D) Data model
- Postgres materialized table `qi_popular_queries_daily`.
- Redis cached lists for hot windows.
- Fields: `tenant_id, segment, query_norm, display_text, count_1d, count_7d, ctr_7d, zero_rate_7d, trend_score, rank_score, as_of_date`.

### E) Data sources
- Query submit events.
- Click/dwell metrics.
- Segment attributes (department/location).

### F) Ranking strategy
- Global tenant list first.
- Segment overlay if enough support (`n>=50` events).
- Exclude single-user dominated queries (privacy k-anon threshold, e.g., k>=5 unique users).

### G) Online serving architecture
- endpoint reads Redis precomputed list.
- fallback Postgres read-through.
- stale-while-revalidate cache.

### H) Offline pipelines
- Hourly incremental aggregate + daily finalize.
- Trend recomputation each hour.
- Backfill from last 90-day logs on tenant onboarding.

### I) Multi-tenancy and access control
- Strict per-tenant aggregates.
- k-anonymity + suppression for low-user queries.
- optional role-scoped popular lists.

### J) Evaluation
- click-through from popular module.
- cold-start query success uplift.

### K) Failure modes / risks
- popularity spam from automated clients.
- stale seasonal terms.
- mitigate with bot filtering and short refresh cadence.

### L) MVP vs roadmap
- **Now:** top successful queries 7d.
- **Later:** segmented trend-aware and seasonal forecasting.

---

## Capability 5: Spelling Correction

### A) Purpose
- Corrects misspelled queries before retrieval to reduce zero-results.
- In Query Intelligence because it is input normalization/preprocessing; retrieval should receive corrected or dual-run query.

### B) Inputs and outputs
**Endpoint:** `POST /v1/query-intelligence/spellcheck`

**Request**
```json
{
  "tenant_id": "t_acme",
  "query": "anual budjet polic",
  "locale": "en-US",
  "mode": "suggest_only"
}
```

**Response**
```json
{
  "original": "anual budjet polic",
  "corrected": "annual budget policy",
  "confidence": 0.93,
  "token_edits": [
    {"from": "anual", "to": "annual"},
    {"from": "budjet", "to": "budget"},
    {"from": "polic", "to": "policy"}
  ],
  "action": "suggest"
}
```

**Latency:** p95 < 35 ms.

### C) Core algorithm / logic
1. Tokenize query.
2. For each token not in dictionary, generate candidates via:
   - BK-tree edit distance <=2,
   - keyboard-distance variants,
   - phonetic fallback (Double Metaphone) for English.
3. Candidate scoring:
   - edit distance prior,
   - token frequency in tenant corpus,
   - contextual bigram likelihood.
4. Compose sentence-level candidate using beam search (beam=5).
5. Decide action:
   - auto-correct only if confidence > 0.97 and zero-result risk high.
   - otherwise suggest.

### D) Data model
- `qi_dictionary_terms(tenant_id, term, freq, source, updated_at)`.
- `qi_bigram_stats(tenant_id, t1, t2, pmi)`.
- In-memory BK-tree/FST built per locale + tenant overlay terms.

### E) Data sources
- Document corpus terms.
- Query logs accepted spell corrections.
- enterprise dictionary (product names, acronyms).

### F) Ranking strategy
- Avoid over-correcting valid rare terms (boost protected glossary terms).
- penalize edits on all-caps acronyms and IDs.
- keep original if confidence low.

### G) Online serving architecture
- spellcheck micro-module in same service process for low latency.
- cache corrected full-query results in Redis (`ttl=1d`).

### H) Offline pipelines
- nightly dictionary refresh from index snapshots.
- weekly mining of new OOV terms with human approval queue.

### I) Multi-tenancy and access control
- base locale dictionary shared, tenant overlay private.
- no cross-tenant custom term sharing.

### J) Evaluation
- correction precision@1.
- zero-result reduction after correction.
- false-correction complaint rate.

### K) Failure modes / risks
- over-correcting names/codes.
- multilingual transliteration errors.
- mitigate via protected terms and locale detection.

### L) MVP vs roadmap
- **Now:** dictionary + edit-distance correction.
- **Later:** contextual neural spell model per locale.

---

## Capability 6: Optional Query Rewrite

### A) Purpose
- Rewrites weak queries into retrieval-optimized form (expansion, disambiguation, structured intent extraction).
- In Query Intelligence to keep retrieval layer simple and observable; rewrite is a controlled pre-processing stage.

### B) Inputs and outputs
**Endpoint:** `POST /v1/query-intelligence/rewrite`

**Request**
```json
{
  "tenant_id": "t_acme",
  "user_id": "u_123",
  "query": "pto contractors",
  "mode": "optional",
  "search_vertical": "policies"
}
```

**Response**
```json
{
  "original": "pto contractors",
  "rewritten": "paid time off policy for contractors",
  "rewrite_type": "abbreviation_expansion",
  "confidence": 0.84,
  "explanations": ["expanded acronym pto", "added domain term policy"],
  "apply": false
}
```

**Latency:** p95 < 90 ms (deterministic), p95 < 180 ms if LLM assist enabled.

### C) Core algorithm / logic
1. Classify query quality (`short`, `ambiguous`, `acronym-heavy`, `natural-question`).
2. Generate rewrites via deterministic rules:
   - acronym expansion from tenant lexicon,
   - synonym substitution,
   - intent template expansion (`benefits` -> `benefits policy`).
3. Optionally call compact LLM rewrite only when deterministic confidence low and budget allows.
4. Validate rewrite with guardrails:
   - semantic drift threshold (embedding cosine >= 0.78 to original intent),
   - max added tokens,
   - forbidden term checks.
5. Set `apply=true` only above high threshold and policy allows auto-apply.

### D) Data model
- `qi_rewrite_rules(tenant_id, pattern, replacement, rule_type, priority, enabled)`.
- `qi_acronym_map(tenant_id, acronym, expansion, confidence)`.
- `qi_rewrite_audit(log_id, tenant_id, user_id_hash, original, rewritten, accepted, outcome)`.

### E) Data sources
- Tenant glossary and acronym list.
- Past query->successful reformulation pairs.
- Domain taxonomy.

### F) Ranking strategy
- Conservative strategy: precision > recall.
- prioritize deterministic trusted rewrites.
- LLM rewrites receive penalty unless validated by retrieval-side gains historically.

### G) Online serving architecture
- `/rewrite` invoked by UI or orchestrator when query quality low.
- strict timeout tiers: rules 20 ms, optional LLM 120 ms max.
- fallback: no rewrite and return rationale.

### H) Offline pipelines
- mine high-confidence rewrite pairs from logs.
- periodic rule curation and approval workflow.
- evaluate candidate rules in shadow mode before enabling.

### I) Multi-tenancy and access control
- tenant-specific rules/glossary only.
- audit every rewrite decision for compliance.

### J) Evaluation
- rewrite acceptance rate.
- downstream NDCG/CTR uplift.
- semantic drift incidents.

### K) Failure modes / risks
- bad rewrites changing intent.
- regulatory/compliance term mutations.
- mitigate with denylist + human-reviewed rule sets.

### L) MVP vs roadmap
- **Now:** deterministic rewrite with conservative apply policy.
- **Later:** LLM rewrite with strict validator and per-tenant policies.

---

## Cross-cutting 1) End-to-end architecture

1. **UI** emits keystrokes and query submit events.
2. **API Gateway** authenticates, injects tenant/user claims.
3. **Query Intelligence Service** handles autocomplete/suggestions/recent/popular/spellcheck/rewrite.
4. UI or orchestrator sends final query to **Enterprise Search Backend**.
5. Search backend fans out to:
   - lexical index (BM25/OpenSearch),
   - semantic retrieval / RAGBuilder (vector recall + re-ranking).
6. Results returned to UI.
7. All interactions logged to **Analytics Pipeline** for offline feature refresh.

**Responsibility split**
- Query Intelligence: query shaping + UX candidate generation + safe filtering.
- Enterprise Search backend: retrieval, ranking, ACL enforcement on documents.
- Semantic/RAG: meaning-based retrieval and answer synthesis.
- Analytics: aggregates, metrics, model/rule refresh artifacts.

---

## Cross-cutting 2) Recommended microservice boundaries

**Phase 1 (single service, modular):**
- One Query Intelligence service with modules:
  - `autocomplete`, `suggestions`, `history(popular+recent)`, `spellcheck`, `rewrite`.
- Shared infra: normalization, safety filter, ranking utils, tenant config.

**Phase 2/3 split (if scale demands):**
- Split hot-path keystroke features (`autocomplete`) into dedicated low-latency service.
- Keep spellcheck+rewrite together as "query transformation" service.
- Keep history/popular as read-heavy cache service.

---

## Cross-cutting 3) API design (REST + optional gRPC)

### REST endpoints
- `POST /v1/query-intelligence/autocomplete`
- `POST /v1/query-intelligence/suggestions`
- `GET /v1/query-intelligence/recent`
- `GET /v1/query-intelligence/popular`
- `POST /v1/query-intelligence/spellcheck`
- `POST /v1/query-intelligence/rewrite`

### Shared response envelope
```json
{
  "request_id": "req_123",
  "tenant_id": "t_acme",
  "data": {},
  "meta": {"latency_ms": 18, "cache": "hit"},
  "errors": []
}
```

### gRPC methods
- `Autocomplete(AutocompleteRequest) returns (AutocompleteResponse)`
- `Suggest(SuggestRequest) returns (SuggestResponse)`
- `GetRecent(GetRecentRequest) returns (GetRecentResponse)`
- `GetPopular(GetPopularRequest) returns (GetPopularResponse)`
- `Spellcheck(SpellcheckRequest) returns (SpellcheckResponse)`
- `Rewrite(RewriteRequest) returns (RewriteResponse)`

---

## Cross-cutting 4) Storage recommendations

- **Redis:** online hot reads/writes (recent, popular cache, prefix candidates, per-query cached spell/rewrite).
- **Postgres:** system-of-record tables, configs/rules, auditable history, aggregates.
- **OpenSearch:** optional for large candidate retrieval and semantic-neighbor query mining.
- **Trie/FST index:** best for millisecond prefix lookup at scale.
- **Vector DB:** not required for MVP; useful later for rewrite/suggestion semantic neighborhoods.

**Tradeoffs**
- Redis fastest but volatile/limited memory.
- Postgres durable but slower for prefix search unless carefully indexed.
- OpenSearch flexible but operationally heavier and higher tail latency.

---

## Cross-cutting 5) Implementation roadmap

### Phase 1 (MVP, weeks 1–2)
- Autocomplete (tenant prefix + popularity).
- Recent searches.
- Popular searches (daily aggregates).
- Deterministic spellcheck suggest-only.
- Safety filtering + tenant isolation hardening.

### Phase 2 (weeks 3–4)
- Query suggestions from session graph + synonyms.
- Basic deterministic rewrite (optional, no auto-apply by default).
- Metrics dashboards + A/B framework.
- Better caching and fallback paths.

### Phase 3 (weeks 5–6+)
- Personalization features.
- LTR ranking for suggestions/autocomplete.
- Guardrailed LLM rewrite assist.
- Segment-aware popular and multilingual expansion.

---

## Cross-cutting 6) Pseudocode

### Autocomplete
```python
def autocomplete(req):
    p = normalize(req.prefix)
    if len(p) < 2: return []
    cands = prefix_index.fetch(req.tenant_id, p, topn=100)
    cands = apply_acl_and_safety(cands, req.context)
    scored = [score_autocomplete(c, req) for c in cands]
    return diversify_and_topk(scored, req.limit)
```

### Suggestions
```python
def suggestions(req):
    q = normalize(req.query)
    pools = [
      synonym_expand(q, req.tenant_id),
      query_graph_neighbors(q, req.tenant_id),
      taxonomy_related(q, req.tenant_id)
    ]
    cands = dedupe(flatten(pools))
    cands = apply_acl_and_safety(cands, req.context)
    return topk(rank_suggestions(cands, req), req.limit)
```

### Recent
```python
def recent(req):
    items = redis.zrevrange(key_recent(req.tenant_id, req.user_id), 0, req.limit-1)
    return filter_sensitive(items)
```

### Popular
```python
def popular(req):
    cached = redis.get(popular_key(req.tenant_id, req.segment, req.window))
    if cached: return cached
    rows = pg.fetch_popular(req.tenant_id, req.segment, req.window)
    return suppress_low_k_anon(rows)
```

### Spellcheck
```python
def spellcheck(req):
    toks = tokenize(req.query)
    lattice = []
    for t in toks:
        lattice.append(candidates_for_token(t, req.tenant_id))
    best = beam_search_sentence(lattice, beam=5)
    conf = confidence(best)
    return build_spell_response(req.query, best, conf)
```

### Rewrite
```python
def rewrite(req):
    q = normalize(req.query)
    cands = deterministic_rewrites(q, req.tenant_id)
    if low_confidence(cands) and llm_enabled(req.tenant_id):
        cands += llm_rewrite(q, timeout_ms=120)
    cands = [c for c in cands if passes_guardrails(q, c)]
    best = select_best(cands)
    return build_rewrite_response(q, best)
```

### Orchestration for one query session
```python
def handle_query_session(event):
    if event.type == "keystroke":
        return autocomplete(event)

    if event.type == "query_submit":
        spell = spellcheck_if_needed(event.query)
        rewrite = rewrite_if_enabled(event.query, spell)
        final_query = choose_final_query(event.query, spell, rewrite, policy=event.tenant_policy)
        log_query_intelligence(event, spell, rewrite, final_query)
        return send_to_search_backend(final_query)
```

---

## Cross-cutting 7) Production concerns

- **Observability:** structured logs with request_id, tenant_id, feature, decision reasons.
- **SLIs/SLOs:**
  - availability 99.9% for autocomplete/recent/popular,
  - p95 latency targets per endpoint,
  - error rate < 0.5%.
- **Dashboards:** per-tenant latency, cache hit, acceptance rate, zero-result rescue.
- **Tracing:** OpenTelemetry spans from API gateway -> query intelligence modules -> Redis/Postgres.
- **Fallbacks:** cache-only mode, disable rewrite/spell auto-apply when dependency degraded.
- **Degradation modes:**
  - level 1: disable personalization,
  - level 2: disable suggestions graph,
  - level 3: serve static taxonomy list.
- **Cost/perf:** keep hot-path in Redis/in-memory; run heavier mining jobs offline.

---

## Cross-cutting 8) Security and privacy

- Store minimal query logs: `tenant_id`, pseudonymous `user_id_hash`, query text (redacted), timestamp, feature decisions.
- **Do not store** raw auth tokens, full PII payloads, unrestricted free-form sensitive fields.
- PII handling:
  - online redaction (emails, SSNs, phone, account numbers) before persistence,
  - encrypted at rest and in transit.
- Retention guidance:
  - raw events 30–90 days,
  - aggregated metrics 12–18 months,
  - user-delete/RTBF pipeline within SLA.
- Tenant isolation:
  - separate logical namespaces, per-tenant encryption keys preferred,
  - row-level security in Postgres,
  - strict IAM for data pipelines.

---

## Recommended MVP architecture

- **Single Query Intelligence service** (FastAPI/Spring Boot) with modular handlers.
- **Redis** for autocomplete/read caches/recent/popular hot paths.
- **Postgres** for configuration, aggregate tables, audit logs.
- **Kafka/Kinesis + batch jobs** for query/click aggregation.
- Deterministic spellcheck + deterministic rewrite (suggest-only by default).
- Hard safety filter + k-anonymity suppression + tenant ACL gating on every returned candidate.

## Recommended data schema (MVP)

- `qi_query_events(event_id, tenant_id, user_id_hash, session_id, query_raw_redacted, query_norm, ts, source_surface)`
- `qi_click_events(event_id, tenant_id, user_id_hash, session_id, query_norm, doc_id, ts, dwell_ms)`
- `qi_autocomplete_candidates(tenant_id, candidate_id, text, normalized_text, source_type, popularity_7d, popularity_30d, last_seen_at, quality_score, is_blocked)`
- `qi_popular_queries_daily(tenant_id, segment, query_norm, display_text, count_1d, count_7d, ctr_7d, zero_rate_7d, trend_score, rank_score, as_of_date)`
- `qi_synonyms(tenant_id, term, expansion, confidence, source, updated_at)`
- `qi_acronym_map(tenant_id, acronym, expansion, confidence, updated_at)`
- `qi_rewrite_rules(tenant_id, pattern, replacement, rule_type, priority, enabled, updated_at)`
- `qi_rewrite_audit(log_id, tenant_id, user_id_hash, original_query_norm, rewritten_query_norm, accepted, outcome, ts)`

## Recommended API contract (MVP)

- REST JSON, tenant inferred from auth claims but also validated against payload.
- Idempotent GET for `recent/popular`, POST for generation/transformation features.
- Shared metadata: `request_id`, `latency_ms`, `cache_status`, `decision_reasons`.
- Error codes:
  - `400` bad input,
  - `401/403` auth/tenant mismatch,
  - `429` rate limit,
  - `503` degraded mode with fallback payload.

## Recommended 6-week implementation plan

**Week 1**
- Service skeleton, auth/tenant middleware, normalization utilities, safety filter, telemetry scaffold.

**Week 2**
- Autocomplete (prefix index + Redis cache) and recent searches end-to-end.

**Week 3**
- Popular searches pipeline (hourly aggregate + endpoint), dashboards for latency/cache/CTR.

**Week 4**
- Spellcheck deterministic pipeline + tenant dictionary ingestion + A/B flags.

**Week 5**
- Query suggestions (synonyms + query graph), fallback logic, rate limiting hardening.

**Week 6**
- Optional rewrite (deterministic), audit logging, shadow evaluation, rollout guardrails, production readiness review.
