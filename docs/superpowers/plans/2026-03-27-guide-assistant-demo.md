# Guide Assistant Demo Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone frontend demo page for `POST /ai/guide/assistant` with a focused operations-console layout.

**Architecture:** Add one static HTML page and one local static-file server script. The page submits structured guide requests to the unified backend entrypoint and renders the response by `route_name`, while preserving raw JSON for debugging.

**Tech Stack:** HTML, Tailwind CDN, vanilla JavaScript, Python standard-library `http.server`

---

## File Map

- Create: `guide_assistant_demo.html`
  - Standalone demo page for the unified guide assistant API
- Create: `scripts/start_guide_assistant_demo.py`
  - Local static file server for the new demo page

## Chunk 1: Page Skeleton And Input Console

### Task 1: Add the standalone demo page shell

**Files:**
- Create: `guide_assistant_demo.html`

- [ ] **Step 1: Create the page shell**

Include:

- title and short description
- API base label
- two-column responsive layout
- input panel on the left
- result panel on the right
- raw JSON panel at the bottom

- [ ] **Step 2: Add the input fields**

Fields to include:

- `query` textarea
- `guide_id` input
- `user_id` input
- `sku` input
- `top_k` number input
- `use_custom_plan` checkbox

Buttons:

- submit
- clear
- quick-fill search example
- quick-fill follow-up example

- [ ] **Step 3: Add empty placeholder states**

Add:

- empty result message before first request
- hidden error banner
- hidden loading state

- [ ] **Step 4: Verify page structure visually by opening the file in editor**

Expected:

- layout sections are clear and self-contained
- no legacy copy-generation sections remain

## Chunk 2: Frontend Request And Rendering Logic

### Task 2: Implement request submission and utility helpers

**Files:**
- Modify: `guide_assistant_demo.html`

- [ ] **Step 1: Add failing-first manual behavior target**

Target behavior:

- clicking submit with a non-empty query sends a request to `/ai/guide/assistant`
- invalid input shows an error banner

- [ ] **Step 2: Add utility helpers**

Implement:

- `showError(message)`
- `hideError()`
- `setLoading(isLoading)`
- `clearForm()`
- `copyJson()`

- [ ] **Step 3: Add quick-fill helpers**

Implement:

- `fillSearchExample()`
- `fillFollowupExample()`

Suggested example payloads:

```js
{
  query: "帮我找几款运动鞋",
  guide_id: "guide_001",
  top_k: 5
}
```

```js
{
  query: "这个用户看了很久，我该怎么回",
  user_id: "user_001",
  sku: "8WZ01CM1",
  guide_id: "guide_001",
  use_custom_plan: true
}
```

- [ ] **Step 4: Implement submit logic**

Implement `submitGuideAssistant()`:

- validate `query`
- build payload from form fields
- `fetch("http://127.0.0.1:8000/ai/guide/assistant")`
- handle non-200 responses
- route successful payload to render helpers

- [ ] **Step 5: Verify JavaScript syntax**

Run: `python -c "from pathlib import Path; compile(Path('guide_assistant_demo.html').read_text(encoding='utf-8'), 'guide_assistant_demo.html', 'exec')"`

Expected:

- this will not fully validate HTML/JS, so use it only to confirm the file is readable as UTF-8
- no file read/encoding error

## Chunk 3: Route-Specific Result Rendering

### Task 3: Render response states by `route_name`

**Files:**
- Modify: `guide_assistant_demo.html`

- [ ] **Step 1: Add result rendering entrypoint**

Implement:

- `renderGuideAssistantResult(data)`

This function should always render:

- route badge
- routing reason
- normalized params
- raw JSON

- [ ] **Step 2: Add vector search rendering**

Implement:

- `renderVectorSearchResult(result)`

Show:

- total count
- ranked cards
- score
- chunk preview

- [ ] **Step 3: Add sales graph rendering**

Implement:

- `renderSalesGraphResult(result)`

Show:

- intent level
- allowed
- anti-disturb blocked
- final message
- optional sales suggestion
- optional message pack list

- [ ] **Step 4: Add unknown rendering**

Implement:

- `renderUnknownResult(result)`

Show a non-error informational card explaining that current inputs do not match a supported route.

- [ ] **Step 5: Verify display logic by manual browser run**

Expected:

- search example shows vector-search result layout
- follow-up example shows sales-graph result layout
- unsupported input shows unknown layout

## Chunk 4: Demo Server

### Task 4: Add a dedicated local server script

**Files:**
- Create: `scripts/start_guide_assistant_demo.py`

- [ ] **Step 1: Copy the minimal static-server pattern from the existing demo server**

Requirements:

- serve files from project root
- set permissive CORS headers
- handle `OPTIONS`
- print the demo URL

- [ ] **Step 2: Point the default page to the new demo**

Suggested URL:

`http://127.0.0.1:8080/guide_assistant_demo.html`

- [ ] **Step 3: Optionally open the browser**

Use `webbrowser.open(...)` behind a best-effort `try/except`.

- [ ] **Step 4: Verify script syntax**

Run:

```bash
python -m py_compile scripts/start_guide_assistant_demo.py
```

Expected: PASS

## Chunk 5: Final Verification

### Task 5: Verify the new demo end to end

**Files:**
- Test target: `guide_assistant_demo.html`
- Test target: `scripts/start_guide_assistant_demo.py`

- [ ] **Step 1: Run syntax checks**

Run:

```bash
python -m py_compile scripts/start_guide_assistant_demo.py
```

Expected: PASS

- [ ] **Step 2: Start the demo server**

Run:

```bash
python scripts/start_guide_assistant_demo.py
```

Expected:

- local URL is printed
- browser opens or URL is usable manually

- [ ] **Step 3: Manual smoke test the page**

Verify:

- page loads
- search quick-fill works
- follow-up quick-fill works
- submit works against local backend
- raw JSON updates
- copy button works

- [ ] **Step 4: Record any environment blockers**

If backend is not running, note that the static page still loads but API actions cannot complete until `http://127.0.0.1:8000` is available.
