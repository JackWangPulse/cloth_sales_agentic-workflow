# Guide Ownership Filter Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce strict `guide_id` ownership filtering on behavior-driven flows so that sales suggestions only use logs that belong to the requesting guide.

**Architecture:** Push ownership enforcement down into behavior retrieval, then propagate the requirement upward through API schemas, graph behavior fetching, and unified guide routing. Search flows stay guide-agnostic; behavior-driven flows must provide `guide_id`.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy repository filters, existing LangGraph sales flow

---

## File Map

- Modify: `app/repositories/behavior_repository.py`
  - Require `guide_id` in behavior queries
- Modify: `app/agents/tools/behavior_tool.py`
  - Pass `context.guide_id` and preserve empty-summary fallback
- Modify: `app/schemas/intent_schemas.py`
  - Require `guide_id` on intent-analysis requests
- Modify: `app/schemas/followup_schemas.py`
  - Require `guide_id` on follow-up requests
- Modify: `app/api/v1/intent.py`
  - Query behavior by `user_id + sku + guide_id`
- Modify: `app/api/v1/followup.py`
  - Query behavior by `user_id + sku + guide_id`
- Modify: `app/services/guide_assistant_router.py`
  - Only route to `sales_graph` when `user_id + sku + guide_id` are all present
- Modify: `guide_assistant_demo.html`
  - Frontend validation for `sales_graph`-style requests missing `guide_id`
- Create: `tests/test_behavior_repository_ownership.py`
- Modify: `tests/test_guide_assistant_router.py`
- Modify: `docs/guide_assistant_api.md`

## Chunk 1: Repository Ownership Filter

### Task 1: Enforce guide ownership in behavior retrieval

**Files:**
- Modify: `app/repositories/behavior_repository.py`
- Create: `tests/test_behavior_repository_ownership.py`

- [ ] **Step 1: Write the failing repository tests**

Cover:

- `guide_id` is required by the repository function
- query filters on `user_id`, `sku`, and `guide_id`

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest tests/test_behavior_repository_ownership.py -v`
Expected: FAIL because the repository does not yet require `guide_id`

- [ ] **Step 3: Implement the minimal repository change**

Change `get_recent_behavior(...)` signature to include `guide_id: str` and add:

```python
UserBehaviorLog.guide_id == guide_id
```

to the filter.

- [ ] **Step 4: Re-run the focused repository test**

Run: `python -m pytest tests/test_behavior_repository_ownership.py -v`
Expected: PASS

## Chunk 2: Propagate Guide Ownership Through Behavior Flows

### Task 2: Require guide ownership in graph and direct APIs

**Files:**
- Modify: `app/agents/tools/behavior_tool.py`
- Modify: `app/schemas/intent_schemas.py`
- Modify: `app/schemas/followup_schemas.py`
- Modify: `app/api/v1/intent.py`
- Modify: `app/api/v1/followup.py`

- [ ] **Step 1: Write failing schema/router tests or update existing ones**

Cover:

- `guide_id` is required for `IntentAnalysisRequest`
- `guide_id` is required for `FollowupRequest`

- [ ] **Step 2: Run targeted tests to verify they fail**

Run: `python -m pytest tests/test_guide_assistant_router.py -v`
Expected: existing router tests may need updates once guide ownership semantics change

- [ ] **Step 3: Update schemas and behavior tool**

Implement:

- `IntentAnalysisRequest.guide_id: str`
- `FollowupRequest.guide_id: str`
- `fetch_behavior_summary(...)` passes `context.guide_id` into `get_recent_behavior(...)`

Keep the empty-summary fallback when `context.guide_id` is missing or query returns no rows.

- [ ] **Step 4: Update direct APIs**

Change intent/followup endpoints to pass `request.guide_id` into the repository query.

- [ ] **Step 5: Re-run focused tests or syntax verification**

Run:

```bash
python -m py_compile app\\repositories\\behavior_repository.py app\\agents\\tools\\behavior_tool.py app\\schemas\\intent_schemas.py app\\schemas\\followup_schemas.py app\\api\\v1\\intent.py app\\api\\v1\\followup.py
```

Expected: PASS

## Chunk 3: Unified Guide Routing And Demo Validation

### Task 3: Make unified guide routing respect guide ownership

**Files:**
- Modify: `app/services/guide_assistant_router.py`
- Modify: `tests/test_guide_assistant_router.py`
- Modify: `guide_assistant_demo.html`

- [ ] **Step 1: Extend router tests with ownership requirement**

Add a test for:

- `user_id + sku` without `guide_id` should not route to `sales_graph`

- [ ] **Step 2: Run router tests to verify failure**

Run: `python -m pytest tests/test_guide_assistant_router.py -v`
Expected: FAIL because router still allows sales_graph without `guide_id`

- [ ] **Step 3: Update router rule**

Only return `sales_graph` when:

```python
request.user_id and request.sku and request.guide_id
```

- [ ] **Step 4: Update demo validation**

In `guide_assistant_demo.html`, if the form looks like a follow-up request (`user_id` or `sku` present) but `guide_id` is empty, show a frontend validation error.

- [ ] **Step 5: Re-run syntax checks**

Run:

```bash
python -m py_compile app\\services\\guide_assistant_router.py
python -c "from pathlib import Path; Path('guide_assistant_demo.html').read_text(encoding='utf-8'); print('ok')"
```

Expected: PASS

## Chunk 4: Documentation And Verification

### Task 4: Document the ownership rule and verify

**Files:**
- Modify: `docs/guide_assistant_api.md`

- [ ] **Step 1: Update documentation**

Document:

- `guide_id` is required for `sales_graph`-style requests
- search requests remain guide-agnostic
- ownership filtering is enforced on behavior logs

- [ ] **Step 2: Run final syntax verification**

Run:

```bash
python -m py_compile app\\repositories\\behavior_repository.py app\\agents\\tools\\behavior_tool.py app\\schemas\\intent_schemas.py app\\schemas\\followup_schemas.py app\\api\\v1\\intent.py app\\api\\v1\\followup.py app\\services\\guide_assistant_router.py
```

Expected: PASS

- [ ] **Step 3: Record environment blockers**

If `pytest` is unavailable, note that targeted tests were written or updated but only syntax verification could be completed in this environment.
