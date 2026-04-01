# Guide Assistant Observability Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cache hit/miss diagnostics and request timing to `/ai/guide/assistant` and surface them in the demo page.

**Architecture:** Track cache hit/miss at the cache service and agent tool layers, aggregate diagnostics in the guide assistant service, and render them in the dedicated demo frontend. Keep changes scoped to the unified entrypoint and shared graph tools it already uses.

**Tech Stack:** FastAPI, Pydantic, existing sales graph flow, Redis cache services, static HTML demo

---

## Chunk 1: Diagnostics contract

### Task 1: Extend guide assistant response with diagnostics

**Files:**
- Modify: `app/schemas/guide_assistant_schemas.py`
- Modify: `tests/test_guide_assistant_service.py`

- [ ] **Step 1: Write failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add diagnostics schema fields**
- [ ] **Step 4: Run test or syntax validation**

## Chunk 2: Backend instrumentation

### Task 2: Aggregate timings and cache metadata

**Files:**
- Modify: `app/services/cache_service.py`
- Modify: `app/services/product_cache_service.py`
- Modify: `app/services/behavior_cache_service.py`
- Modify: `app/agents/tools/product_tool.py`
- Modify: `app/agents/tools/behavior_tool.py`
- Modify: `app/services/guide_assistant_service.py`

- [ ] **Step 1: Write failing tests for diagnostics payload**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Add cache hit/miss logging and diagnostics propagation**
- [ ] **Step 4: Run test or syntax validation**

## Chunk 3: Frontend rendering

### Task 3: Show diagnostics in the demo page

**Files:**
- Modify: `guide_assistant_demo.html`

- [ ] **Step 1: Render diagnostics card in the result panel**
- [ ] **Step 2: Show timing and cache status**
- [ ] **Step 3: Run HTML/readability checks**
