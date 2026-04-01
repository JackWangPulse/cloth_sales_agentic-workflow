# Redis Mainline Cache Design

## Goal

Add Redis caching to the mainline read-heavy paths of the project to reduce
database pressure and repeated behavior-intent computation.

First phase scope:

- cache product lookup by `sku`
- cache behavior summary by `guide_id + user_id + sku + limit`
- cache intent result by `guide_id + user_id + sku + limit`

## Why This Scope

These are the most valuable cache targets right now:

- product lookup is high-frequency and relatively stable
- behavior summary is repeatedly recomputed from the same logs
- intent result is derived from behavior summary and is also frequently reused

Out of scope for phase one:

- caching full `sales_graph` result
- caching final follow-up messages
- caching raw behavior log lists

## Architecture

Keep repository responsibilities unchanged and add a thin cache-service layer on
top.

Recommended files:

- `app/services/cache_service.py`
- `app/services/product_cache_service.py`
- `app/services/behavior_cache_service.py`

Responsibilities:

- `cache_service.py`
  - Redis connection management
  - JSON get/set helpers
  - graceful fallback when Redis is unavailable

- `product_cache_service.py`
  - cache-aside for `product by sku`

- `behavior_cache_service.py`
  - cache-aside for `behavior_summary`
  - cache-aside for `intent_result`

## Cache Keys

### Product

Key:

`product:sku:{sku}`

TTL:

- 1800 seconds

### Behavior Summary

Key:

`behavior_summary:{guide_id}:{user_id}:{sku}:{limit}`

TTL:

- 300 seconds

### Intent Result

Key:

`intent:{guide_id}:{user_id}:{sku}:{limit}`

TTL:

- 300 seconds

## Data Shape

### Product Cache Value

Store only serializable product fields that are actually used by the mainline:

- `sku`
- `name`
- `price`
- `tags`
- `attributes`
- optional `brand_code`

### Behavior Summary Cache Value

Store the same summary shape already used by the behavior tool and direct APIs:

- `visit_count`
- `max_stay_seconds`
- `avg_stay_seconds`
- `total_stay_seconds`
- `has_enter_buy_page`
- `has_favorite`
- `has_share`
- `has_click_size_chart`
- `event_types`
- `event_type_counts`

### Intent Cache Value

Store:

- `intent_level`
- `reason`
- `behavior_summary`

This avoids recomputing the same summary-intent combination within the TTL.

## Integration Points

### Product Path

Use cache before database product fetch in the mainline path that powers:

- `sales_graph`
- `agent_sales_flow`
- unified guide assistant follow-up flow

Do not change the underlying repository API in phase one unless needed.

### Behavior Path

Use cache around behavior summary generation in:

- `app/agents/tools/behavior_tool.py`
- direct `intent` API
- direct `followup` API

### Intent Path

Use cache around `classify_intent(...)` where behavior summary is already available.

## Fallback Rules

If Redis is unavailable:

- log warning once per path
- skip cache access
- continue with database and in-process computation

Redis must remain optional.

## Invalidations

Phase one uses TTL-based invalidation only.

Reasons:

- simpler
- enough for current behavior freshness requirement
- avoids adding write-path coupling too early

## Error Handling

Cache failures must never break the request path.

Rules:

- Redis get failure -> log and continue
- Redis set failure -> log and continue
- JSON decode failure -> treat as cache miss

## Verification

Need focused tests for:

- cache key generation
- cache miss -> DB path -> set cache
- cache hit -> skip DB
- Redis unavailable -> graceful fallback

## Non-Goals

- no write-through caching
- no cache invalidation hooks on ETL/update paths yet
- no caching of final generated copy/messages in phase one
