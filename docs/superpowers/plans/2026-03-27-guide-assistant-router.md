# Guide Assistant Router Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a unified guide assistant entrypoint that accepts structured fields plus a natural-language query, routes requests to either `vector_search` or `sales_graph`, and returns a normalized response with routing metadata.

**Architecture:** Introduce a thin API endpoint, a router service for intent-to-capability dispatch, and an execution service that calls internal capabilities directly instead of making HTTP requests back into the same app. Start with rule-based routing only; do not add LLM routing in the first version.

**Tech Stack:** FastAPI, Pydantic, existing vector search service logic, existing sales graph runner, pytest

---

## File Map

- Create: `app/api/v1/guide_assistant.py`
  - Unified API entrypoint `POST /ai/guide/assistant`
- Create: `app/services/guide_assistant_router.py`
  - Rule-based routing and parameter normalization
- Create: `app/services/guide_assistant_service.py`
  - Dispatch to internal execution paths for `vector_search` and `sales_graph`
- Create: `app/schemas/guide_assistant_schemas.py`
  - Request/response schemas and route enums
- Create: `tests/test_guide_assistant_router.py`
  - Unit tests for routing rules and normalized params
- Create: `tests/test_guide_assistant_service.py`
  - Service-level dispatch tests
- Create: `tests/test_guide_assistant_api.py`
  - API endpoint tests
- Modify: `app/main.py`
  - Register new router
- Modify: `app/api/v1/vector_search.py`
  - Extract reusable internal search helper if needed
- Modify: `app/api/v1/sales_graph.py`
  - Extract reusable internal execution helper if needed
- Modify: `README.md`
  - Add unified guide assistant entrypoint usage
- Modify: `docs/sales_graph_api.md`
  - Cross-reference unified guide assistant entrypoint
- Create: `docs/guide_assistant_api.md`
  - Dedicated endpoint documentation

## Chunk 1: Schemas And Router Rules

### Task 1: Add request and response schemas

**Files:**
- Create: `app/schemas/guide_assistant_schemas.py`
- Test: `tests/test_guide_assistant_router.py`

- [ ] **Step 1: Write the failing schema and routing tests**

```python
def test_sales_graph_route_when_user_id_and_sku_present():
    request = GuideAssistantRequest(
        query="这个用户看了很久，我该怎么回",
        user_id="user_001",
        sku="8WZ01CM1",
        guide_id="guide_001",
    )
    decision = route_guide_request(request)
    assert decision.route_name == "sales_graph"


def test_vector_search_route_for_search_intent_query():
    request = GuideAssistantRequest(
        query="帮我找几款运动鞋",
        guide_id="guide_001",
        top_k=5,
    )
    decision = route_guide_request(request)
    assert decision.route_name == "vector_search"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_guide_assistant_router.py -v`
Expected: FAIL because schema/router files do not exist yet

- [ ] **Step 3: Add schema models**

```python
class GuideAssistantRequest(BaseModel):
    query: str
    user_id: str | None = None
    sku: str | None = None
    guide_id: str | None = None
    top_k: int = 5
    use_custom_plan: bool = False


class RouteDecision(BaseModel):
    route_name: str
    reason: str
    normalized_params: dict[str, Any]
```

- [ ] **Step 4: Re-run tests**

Run: `python -m pytest tests/test_guide_assistant_router.py -v`
Expected: FAIL at router logic assertions, not import errors

- [ ] **Step 5: Commit**

```bash
git add app/schemas/guide_assistant_schemas.py tests/test_guide_assistant_router.py
git commit -m "feat: add guide assistant schemas"
```

### Task 2: Implement rule-based router

**Files:**
- Create: `app/services/guide_assistant_router.py`
- Test: `tests/test_guide_assistant_router.py`

- [ ] **Step 1: Write one failing rule test per route**

```python
def test_unknown_route_when_insufficient_inputs():
    request = GuideAssistantRequest(query="帮我处理一下")
    decision = route_guide_request(request)
    assert decision.route_name == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_guide_assistant_router.py -v`
Expected: FAIL because `route_guide_request` is missing

- [ ] **Step 3: Implement minimal router**

```python
SEARCH_KEYWORDS = ("找", "推荐", "搜", "运动鞋", "通勤鞋", "跑鞋")


def route_guide_request(request: GuideAssistantRequest) -> RouteDecision:
    if request.user_id and request.sku:
        return RouteDecision(
            route_name="sales_graph",
            reason="Detected user_id and sku; suitable for follow-up recommendation flow",
            normalized_params={...},
        )
    if any(keyword in request.query for keyword in SEARCH_KEYWORDS):
        return RouteDecision(
            route_name="vector_search",
            reason="Detected search intent in query",
            normalized_params={...},
        )
    return RouteDecision(
        route_name="unknown",
        reason="Could not determine route from current inputs",
        normalized_params={...},
    )
```

- [ ] **Step 4: Re-run router tests**

Run: `python -m pytest tests/test_guide_assistant_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/guide_assistant_router.py tests/test_guide_assistant_router.py
git commit -m "feat: add rule-based guide assistant router"
```

## Chunk 2: Internal Execution Service

### Task 3: Add execution service for vector search and sales graph

**Files:**
- Create: `app/services/guide_assistant_service.py`
- Modify: `app/api/v1/vector_search.py`
- Modify: `app/api/v1/sales_graph.py`
- Test: `tests/test_guide_assistant_service.py`

- [ ] **Step 1: Write failing dispatch tests**

```python
@pytest.mark.asyncio
async def test_execute_sales_graph_dispatches_to_sales_graph():
    decision = RouteDecision(
        route_name="sales_graph",
        reason="...",
        normalized_params={"user_id": "user_001", "sku": "8WZ01CM1", "guide_id": "guide_001"},
    )
    result = await execute_guide_request(decision)
    assert result["route_name"] == "sales_graph"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_guide_assistant_service.py -v`
Expected: FAIL because execution service does not exist

- [ ] **Step 3: Extract or add internal helpers**

Implementation target:
- `app/api/v1/vector_search.py`
  - Add a reusable helper for performing search from normalized params without going through HTTP
- `app/api/v1/sales_graph.py`
  - Add a reusable helper that executes the sales graph flow and returns plain data

Keep helpers small and route-agnostic.

- [ ] **Step 4: Implement dispatcher service**

```python
async def execute_guide_request(decision: RouteDecision) -> dict[str, Any]:
    if decision.route_name == "vector_search":
        result = await execute_vector_search_internal(...)
    elif decision.route_name == "sales_graph":
        result = await execute_sales_graph_internal(...)
    else:
        result = {"route_name": "unknown", "result": None}
    return {
        "route_name": decision.route_name,
        "reason": decision.reason,
        "normalized_params": decision.normalized_params,
        "result": result,
    }
```

- [ ] **Step 5: Re-run service tests**

Run: `python -m pytest tests/test_guide_assistant_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/guide_assistant_service.py app/api/v1/vector_search.py app/api/v1/sales_graph.py tests/test_guide_assistant_service.py
git commit -m "feat: add guide assistant execution service"
```

## Chunk 3: Unified API Endpoint

### Task 4: Add guide assistant API route

**Files:**
- Create: `app/api/v1/guide_assistant.py`
- Modify: `app/main.py`
- Test: `tests/test_guide_assistant_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_guide_assistant_returns_route_name_and_result(client):
    response = client.post(
        "/ai/guide/assistant",
        json={
            "query": "帮我找几款运动鞋",
            "guide_id": "guide_001",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["route_name"] == "vector_search"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_guide_assistant_api.py -v`
Expected: FAIL because endpoint is missing

- [ ] **Step 3: Implement API route**

```python
@router.post("/guide/assistant", response_model=BaseResponse[GuideAssistantResponse])
async def guide_assistant(request: GuideAssistantRequest):
    decision = route_guide_request(request)
    payload = await execute_guide_request(decision)
    return BaseResponse(code=200, message="success", data=payload)
```

- [ ] **Step 4: Register router in main**

Modify `app/main.py` to include:

```python
from app.api.v1 import guide_assistant as guide_assistant_router
app.include_router(guide_assistant_router.router)
```

- [ ] **Step 5: Re-run API tests**

Run: `python -m pytest tests/test_guide_assistant_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/api/v1/guide_assistant.py app/main.py tests/test_guide_assistant_api.py
git commit -m "feat: add unified guide assistant API"
```

## Chunk 4: Docs And Verification

### Task 5: Document the new entrypoint

**Files:**
- Create: `docs/guide_assistant_api.md`
- Modify: `README.md`
- Modify: `docs/sales_graph_api.md`

- [ ] **Step 1: Add endpoint documentation**

Document:
- request schema
- route decision rules
- example for `vector_search`
- example for `sales_graph`
- example for `unknown`

- [ ] **Step 2: Update README**

Add a short section:
- what the unified entrypoint is
- which two routes it supports in v1

- [ ] **Step 3: Cross-link from sales graph doc**

Mention that guide-facing clients can also use `/ai/guide/assistant`.

- [ ] **Step 4: Commit**

```bash
git add docs/guide_assistant_api.md README.md docs/sales_graph_api.md
git commit -m "docs: add guide assistant entrypoint documentation"
```

### Task 6: Full verification

**Files:**
- Test: `tests/test_guide_assistant_router.py`
- Test: `tests/test_guide_assistant_service.py`
- Test: `tests/test_guide_assistant_api.py`

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m pytest tests/test_guide_assistant_router.py tests/test_guide_assistant_service.py tests/test_guide_assistant_api.py -v
```

Expected: PASS

- [ ] **Step 2: Run adjacent regression tests**

Run:

```bash
python -m pytest tests/test_mandatory_nodes.py tests/test_sales_suggestion.py -v
```

Expected: PASS

- [ ] **Step 3: Smoke test the API manually**

Run:

```bash
curl -X POST http://127.0.0.1:8000/ai/guide/assistant ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"帮我找几款运动鞋\",\"guide_id\":\"guide_001\"}"
```

Expected:
- `route_name=vector_search`
- non-empty `result.results`

Then:

```bash
curl -X POST http://127.0.0.1:8000/ai/guide/assistant ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"这个用户看了很久，我该怎么回\",\"user_id\":\"user_001\",\"sku\":\"8WZ01CM1\",\"guide_id\":\"guide_001\"}"
```

Expected:
- `route_name=sales_graph`
- non-empty `result.sales_suggestion`

- [ ] **Step 4: Commit final verification**

```bash
git add .
git commit -m "test: verify guide assistant router flow"
```
