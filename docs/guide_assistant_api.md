# Guide Assistant API

## Endpoint

`POST /ai/guide/assistant`

This is a unified guide-facing entrypoint. It accepts a natural-language `query`
plus structured fields such as `user_id`, `sku`, and `guide_id`, then routes
the request to one of the supported internal capabilities.

V1 supports:

- `vector_search`
- `sales_graph`

## Request

```json
{
  "query": "find a few running shoes",
  "guide_id": "guide_001",
  "top_k": 5
}
```

```json
{
  "query": "this customer stayed on the product for a long time, how should I reply",
  "user_id": "user_001",
  "sku": "8WZ01CM1",
  "guide_id": "guide_001",
  "use_custom_plan": true
}
```

## Routing Rules

The first version is rule-based.

- If `user_id`, `sku`, and `guide_id` are all present, route to `sales_graph`
- If the query contains search intent such as `find`, `recommend`, `shoes`, or category keywords, route to `vector_search`
- Otherwise return `unknown`

Behavior-driven flows now enforce strict guide ownership filtering. Matching user
behavior logs must belong to the same `guide_id` that is provided in the request.

## Response

```json
{
  "success": true,
  "message": "Guide assistant request executed successfully",
  "data": {
    "route_name": "vector_search",
    "reason": "Detected product search intent from query.",
    "normalized_params": {
      "query": "find a few running shoes",
      "guide_id": "guide_001",
      "top_k": 5
    },
    "result": {
      "query": "find a few running shoes",
      "results": [],
      "total": 0
    }
  }
}
```

## Notes

- The entrypoint dispatches internally; it does not make HTTP calls back into the same service.
- `sales_graph` still owns follow-up recommendation generation.
- `vector_search` returns a lightweight internal search result shape.
- Redis is optional. If `REDIS_URL` is configured and Redis is reachable, product reads may be served from `product:sku:{sku}`.
- Guide-scoped behavior summaries and intent results may be served from `behavior_summary:{guide_id}:{user_id}:{sku}:{limit}` and `intent:{guide_id}:{user_id}:{sku}:{limit}`.
- If Redis is unavailable, the service falls back to the existing database path.
