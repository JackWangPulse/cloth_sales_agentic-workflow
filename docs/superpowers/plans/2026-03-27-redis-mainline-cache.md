# Redis Mainline Cache Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Redis cache-aside support for `product by sku`, `behavior_summary`, and `intent_result` on the mainline read path.

**Architecture:** Introduce a small Redis helper plus focused cache services for product and behavior/intention, then wire them into existing mainline flows. Redis stays optional and all cache failures degrade to current DB behavior.

**Tech Stack:** Redis client, FastAPI, SQLAlchemy, existing behavior and sales graph services

---

## File Map

- Create: `app/services/cache_service.py`
- Create: `app/services/product_cache_service.py`
- Create: `app/services/behavior_cache_service.py`
- Modify: `app/agents/tools/behavior_tool.py`
- Modify: `app/api/v1/intent.py`
- Modify: `app/api/v1/followup.py`
- Modify: `app/api/v1/sales_graph.py`
- Modify: `app/services/guide_assistant_service.py`
- Create: `tests/test_cache_service.py`
- Create: `tests/test_product_cache_service.py`
- Create: `tests/test_behavior_cache_service.py`
- Modify: `docs/guide_assistant_api.md`

## Chunk 1: Redis Helper

### Task 1: Add a safe Redis helper layer

**Files:**
- Create: `app/services/cache_service.py`
- Create: `tests/test_cache_service.py`

- [ ] **Step 1: Write failing tests**

Cover:

- no `redis_url` -> helper returns no client
- JSON set/get helpers work on mocked client
- Redis exceptions degrade to cache miss

- [ ] **Step 2: Run focused tests to verify failure**

Run: `python -m pytest tests/test_cache_service.py -v`
Expected: FAIL because helper file does not exist

- [ ] **Step 3: Implement minimal helper**

Add:

- lazy client creation from `settings.redis_url`
- `get_json(key)`
- `set_json(key, value, ttl_seconds)`
- decode failures treated as misses

- [ ] **Step 4: Re-run focused tests**

Run: `python -m pytest tests/test_cache_service.py -v`
Expected: PASS

## Chunk 2: Product Cache

### Task 2: Cache product lookup by SKU

**Files:**
- Create: `app/services/product_cache_service.py`
- Create: `tests/test_product_cache_service.py`
- Modify: `app/api/v1/sales_graph.py`
- Modify: `app/services/guide_assistant_service.py`

- [ ] **Step 1: Write failing tests**

Cover:

- cache key generation
- cache hit returns cached product payload
- cache miss loads from DB path and backfills Redis

- [ ] **Step 2: Run focused tests to verify failure**

Run: `python -m pytest tests/test_product_cache_service.py -v`
Expected: FAIL because cache service does not exist

- [ ] **Step 3: Implement product cache service**

Use key:

`product:sku:{sku}`

TTL:

`1800`

- [ ] **Step 4: Wire into mainline product path**

Prefer sales-facing flows first:

- `sales_graph`
- unified guide assistant follow-up path

- [ ] **Step 5: Re-run focused tests or syntax validation**

Run:

```bash
python -m py_compile app\\services\\product_cache_service.py app\\api\\v1\\sales_graph.py app\\services\\guide_assistant_service.py
```

Expected: PASS

## Chunk 3: Behavior And Intent Cache

### Task 3: Cache behavior summary and intent result

**Files:**
- Create: `app/services/behavior_cache_service.py`
- Create: `tests/test_behavior_cache_service.py`
- Modify: `app/agents/tools/behavior_tool.py`
- Modify: `app/api/v1/intent.py`
- Modify: `app/api/v1/followup.py`

- [ ] **Step 1: Write failing tests**

Cover:

- behavior summary key generation
- intent key generation
- cache hit bypasses recomputation
- cache miss computes and backfills

- [ ] **Step 2: Run focused tests to verify failure**

Run: `python -m pytest tests/test_behavior_cache_service.py -v`
Expected: FAIL because behavior cache service does not exist

- [ ] **Step 3: Implement behavior cache service**

Keys:

- `behavior_summary:{guide_id}:{user_id}:{sku}:{limit}`
- `intent:{guide_id}:{user_id}:{sku}:{limit}`

TTL:

- `300`

- [ ] **Step 4: Wire into behavior and intent paths**

Use cache in:

- `behavior_tool`
- direct `intent` API
- direct `followup` API

- [ ] **Step 5: Re-run focused tests or syntax validation**

Run:

```bash
python -m py_compile app\\services\\behavior_cache_service.py app\\agents\\tools\\behavior_tool.py app\\api\\v1\\intent.py app\\api\\v1\\followup.py
```

Expected: PASS

## Chunk 4: Docs And Verification

### Task 4: Document cache behavior and verify

**Files:**
- Modify: `docs/guide_assistant_api.md`

- [ ] **Step 1: Update docs**

Document:

- Redis is optional
- product and behavior-intent reads may be served from cache
- behavior cache keys are guide-scoped

- [ ] **Step 2: Run final syntax validation**

Run:

```bash
python -m py_compile app\\services\\cache_service.py app\\services\\product_cache_service.py app\\services\\behavior_cache_service.py app\\agents\\tools\\behavior_tool.py app\\api\\v1\\intent.py app\\api\\v1\\followup.py app\\api\\v1\\sales_graph.py app\\services\\guide_assistant_service.py
```

Expected: PASS

- [ ] **Step 3: Record environment blockers**

If Redis is not running locally, note that code falls back to the current no-cache path.
