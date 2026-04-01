# Guide Assistant Demo Design

## Goal

Add a focused frontend demo for the unified guide assistant entrypoint:

- API target: `POST /ai/guide/assistant`
- Audience: guide-facing internal demo and debugging
- Scope: new standalone page only, without mixing in the older demo features

The page should make it easy to test the two currently supported routes:

- `vector_search`
- `sales_graph`

## Recommended Approach

Use a standalone single-page operations console.

Reasons:

- Fits the current backend shape: one unified endpoint with structured fields
- Easier to debug than a chat-style interface
- Easier to demo than a multi-tab productized console
- Can clearly expose route decision, normalized params, and raw JSON

## Files

Create:

- `guide_assistant_demo.html`
- `scripts/start_guide_assistant_demo.py`

No backend changes are required for this demo page.

## Layout

Use a two-column desktop layout and stacked mobile layout.

### Top Header

- Page title: Guide Assistant Demo
- Small description: unified guide-facing entrypoint
- API base display: `http://127.0.0.1:8000`
- Two quick-fill buttons:
  - search example
  - follow-up example

### Left Column: Input Panel

Fields:

- `query` textarea
- `guide_id` input
- `user_id` input
- `sku` input
- `top_k` input
- `use_custom_plan` checkbox

Actions:

- primary submit button
- clear button

Validation:

- `query` required
- `top_k` numeric
- no requirement that `user_id` and `sku` must both exist, because unknown route is valid

### Right Column: Result Panel

Always show:

- route badge
- routing reason
- normalized params card

Conditional sections:

- `vector_search`
  - result count
  - ranked result cards
  - score
  - chunk preview

- `sales_graph`
  - intent level
  - allowed
  - anti-disturb blocked
  - final message
  - sales suggestion card if present
  - optional message pack list

- `unknown`
  - guidance note explaining that current inputs do not match a supported route

### Bottom Section

- raw JSON viewer
- copy response button

## Interaction Flow

1. User fills the form
2. Page sends request to `/ai/guide/assistant`
3. UI shows loading state
4. Response is rendered by `route_name`
5. Raw JSON is always preserved in technical view

## Frontend Functions

Suggested functions:

- `fillSearchExample()`
- `fillFollowupExample()`
- `clearForm()`
- `submitGuideAssistant()`
- `renderGuideAssistantResult(data)`
- `renderVectorSearchResult(result)`
- `renderSalesGraphResult(result)`
- `renderUnknownResult(result)`
- `renderNormalizedParams(params)`
- `renderRawJson(payload)`
- `copyJson()`
- `showError(message)`
- `hideError()`
- `setLoading(isLoading)`

## Demo Server

`scripts/start_guide_assistant_demo.py` should follow the same pattern as the existing demo server:

- serve static files from project root
- allow CORS headers for local browser usage
- print local demo URL
- optionally open the browser automatically

Suggested URL:

- `http://127.0.0.1:8080/guide_assistant_demo.html`

## Visual Direction

Stay close to the current demo's pragmatic tone, but cleaner and more focused:

- light background
- strong section cards
- status badges with clear color coding
- monospace JSON area
- desktop-first split layout

Do not mix unrelated legacy modules into the page.

## Error Handling

Show a visible error banner when:

- API request fails
- backend returns non-200
- response shape is missing expected fields

Unknown route is not an error; it should render as a valid state.

## Testing

Verification target:

- page loads under the local static server
- search example routes to `vector_search`
- follow-up example routes to `sales_graph`
- raw JSON updates correctly
- copy button works

## Non-Goals

- no chat UI
- no old `generate/copy` widget
- no vision demo integration
- no backend behavior changes
