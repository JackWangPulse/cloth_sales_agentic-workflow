# Guide Assistant Observability Design

**Goal**

Make `/ai/guide/assistant` show whether cache-backed reads were used and how long the request took, both in logs and in the demo page.

**Scope**

- Only enhance `/ai/guide/assistant`
- Keep existing downstream APIs compatible
- Add cache hit/miss logging for Redis-backed product and behavior reads
- Return request diagnostics to the guide assistant frontend

**Design**

- Cache-backed services log `HIT`, `MISS`, and `BYPASS` with cache key and domain.
- `fetch_product` and `fetch_behavior_summary` store cache status in `AgentContext.extra["cache_diagnostics"]`.
- `/ai/guide/assistant` measures total duration and carries downstream duration plus cache diagnostics in a new `diagnostics` field.
- The demo page renders a diagnostics card with total time, downstream time, route, and cache status.

**Non-Goals**

- Do not change `/ai/sales/graph`, `/ai/analyze/intent`, or `/ai/followup/suggest` response contracts.
- Do not add new caching domains beyond the existing product and behavior paths.
