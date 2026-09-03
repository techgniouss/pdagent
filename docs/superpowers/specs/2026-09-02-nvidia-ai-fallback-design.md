# NVIDIA NIM AI Fallback — Design Spec

Date: 2026-09-02
Status: Approved by user, pending implementation plan

## Problem

The bot's AI backend (`GeminiClient` in `pocket_desk_agent/gemini_client.py`) has
one Gemini-family backend selectable via `Config.GEMINI_AUTH_MODE`
(`antigravity` OAuth / `gemini-cli` OAuth / `apikey`). All three modes share
Google's underlying quota. When that quota is exhausted (429
`RESOURCE_EXHAUSTED`, confirmed as the primary reported symptom), the bot goes
fully unresponsive to AI chat and tool-calling until the quota resets — there
is no other backend to fall back to.

## Goal

Add NVIDIA NIM (`https://integrate.api.nvidia.com/v1`, OpenAI-compatible
`/chat/completions`) as a second, independent AI provider. Let the user:

- configure a provider preference order (which one is tried first),
- supply the NVIDIA API key either through the setup wizard or from chat,
- get automatic fallback to the next provider in the order when the current
  one fails with a retryable error (quota, transport, model-not-found),
- keep full tool-calling parity — file ops, screenshots, automation tools
  work identically no matter which provider answered.

## Non-goals

- No third provider in this pass (design should not preclude adding one).
- No per-authorized-user provider preference — this bot is a single-operator
  personal desktop agent; `AUTHORIZED_USER_IDS` are people who can operate
  it, not separate tenants. Provider order is one global `Config` setting,
  consistent with how `GEMINI_AUTH_MODE` already works.
- No change to Gemini's own internal endpoint/model fallback logic
  (`_request_with_model_fallbacks`, `_candidate_model_names`) — that stays
  as Gemini's own internal resilience; the new router sits one level above
  it, across providers.

## Architecture

```
handlers/core.py (handle_message, enhance_command, image handlers)
        │
        ▼
   ai_router.AIRouter          ← new: single entry point, replaces direct
        │  .send_message()       gemini_client calls in core.py
        │  .send_message_with_image()
        ├──> GeminiClient        (existing, narrow changes — see below)
        └──> NvidiaClient        (new, nvidia_client.py)
                  │
                  ▼
        ai_history.py            ← new: shared Gemini-shaped history +
                                    Gemini⇄OpenAI tool/message translation
```

**Canonical history format stays Gemini's `contents`/`parts` shape** — it's
already what `GeminiClient.sessions[user_id]` holds. `NvidiaClient` doesn't
get its own session store; it converts the shared history to OpenAI
`messages` on each call and converts NVIDIA's `tool_calls` / assistant
message back into the same `functionCall` / `functionResponse` / `text`
parts Gemini uses before appending to the shared history. This means a
conversation can start on Gemini, fail over to NVIDIA mid-conversation, and
fail back later, with both providers reading/writing one consistent history
— no dual-session drift.

## Components

### `GeminiClient` (existing — narrow, mechanical changes only)

Two changes, both mechanical:

1. `send_message` / `send_message_with_image` return `ProviderResult`
   instead of a bare `str`. Every place inside `GeminiClient` that currently
   `return`s a string (success text, `_SESSION_EXPIRED_MESSAGE`, `f"Error
   contacting Gemini: {err}"`) instead returns `ProviderResult(text=...,
   is_retryable_error=..., error_message=...)`. This is a breaking signature
   change, but its only two callers today (`core.py`'s `handle_message` /
   `enhance_command` / `_reply_with_gemini_image_analysis`) are migrating to
   `ai_router` in this same change, so nothing is left calling the old
   `str`-returning signature.
2. The tool-call turn body inside the `for turn in range(max_turns):` loop
   (allowlist check via `_ALLOWED_TOOLS`, `_normalize_tool_call`, dispatch
   to `file_manager.*` / `dispatch_gemini_tool`, appending
   `functionCall`/`functionResponse` parts to history) is extracted
   verbatim into `ai_tool_loop.run_tool_turn(...)` and called from both
   `GeminiClient` and `NvidiaClient`, so the security-relevant allowlist
   logic exists in exactly one place.

Everything else — endpoint/model fallback (`_request_with_model_fallbacks`,
`_candidate_model_names`), the three auth modes, retry/backoff on 429,
auto-logout on auth error — is unchanged.

### `pocket_desk_agent/ai_history.py` (new)

Pure-function converters, unit-testable in isolation:

- `gemini_tools_to_openai(function_declarations: list) -> list[dict]` —
  wraps each Gemini `functionDeclarations` entry as an OpenAI
  `{"type": "function", "function": {...}}` tool spec. JSON Schema shapes
  are compatible enough (`type`/`properties`/`required`) to reuse directly.
- `gemini_history_to_openai(history: list, system_prompt: str) -> list[dict]`
  — walks the shared `contents` list and produces an OpenAI `messages` list:
  `role: "user"/"model"` → `"user"/"assistant"`, a `functionCall` part →
  an assistant message with `tool_calls`, a `functionResponse` part → a
  `"tool"` role message keyed by `tool_call_id`. Gemini has no native
  `tool_call_id`; the converter synthesizes one deterministically per
  call so the paired response message can reference it (e.g.
  `f"call_{index}"` by position in the walked history).
- `openai_message_to_gemini_parts(message: dict) -> list[dict]` — converts
  one OpenAI assistant response (text and/or `tool_calls`) back into Gemini
  `parts` (`{"text": ...}` / `{"functionCall": {"name", "args"}}`) so it can
  be appended to the shared history and handled by the *same* tool-dispatch
  code path `GeminiClient.send_message` already uses.

### `pocket_desk_agent/nvidia_client.py` (new)

`NvidiaClient` mirrors `GeminiClient`'s external surface so the router can
treat both uniformly:

```python
class NvidiaClient:
    def __init__(self): ...
    async def send_message(self, user_id, message, file_manager,
                            tool_runtime=None, history=None) -> ProviderResult: ...
    async def send_message_with_image(self, user_id, message, image_bytes,
                                       history=None) -> ProviderResult: ...
```

- Same tool-call loop shape as `GeminiClient.send_message` (turn loop,
  `_ALLOWED_TOOLS` allowlist enforcement, `dispatch_gemini_tool` reuse) —
  the loop body is lifted into a small shared helper
  (`ai_tool_loop.run_tool_turn(func_name, args, ...)`) so the allowlist and
  dispatch logic isn't duplicated between the two clients and can't drift.
- Auth: single `NVIDIA_API_KEY` (`nvapi-...`), sent as `Authorization:
  Bearer` — no OAuth, no per-user tokens.
- Vision: NVIDIA's OpenAI-compatible endpoint accepts image content parts
  (`{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,..."}}`)
  on models that support vision; if the configured `NVIDIA_MODEL` doesn't,
  the call fails and the router's normal fallback/error path handles it
  (image support isn't guaranteed across every NIM model, unlike Gemini).
- Returns a small `ProviderResult` dataclass (`text`, `is_retryable_error`,
  `error_message`) instead of a bare string, so the router can distinguish
  "done, here's the answer" from "failed, try the next provider" without
  string-sniffing.

### `pocket_desk_agent/ai_router.py` (new)

```python
class AIRouter:
    def __init__(self, gemini: GeminiClient, nvidia: NvidiaClient): ...
    def configured_providers(self) -> list[str]: ...   # order, minus unconfigured ones
    async def send_message(self, user_id, message, file_manager, tool_runtime=None) -> str: ...
    async def send_message_with_image(self, user_id, message, image_bytes) -> str: ...
    def clear_session(self, user_id): ...               # delegates to gemini_client.sessions
    @property
    def sessions(self): ...                              # passthrough for /status's `in` check
```

- Reads `Config.AI_PROVIDER_ORDER` (e.g. `["gemini", "nvidia"]`), skips a
  provider that isn't configured (`gemini` needs `auth_client.is_authenticated`
  *or* apikey mode; `nvidia` needs `NVIDIA_API_KEY` set).
- Tries providers in order. A provider's `ProviderResult.is_retryable_error`
  (quota/429 after its own internal retries are exhausted, transport error,
  model-not-found after its own internal fallback list) advances to the
  next provider. Gemini's existing auto-logout-on-auth-error path still
  runs, but the router treats that as retryable too (falls through to
  NVIDIA) rather than returning `_SESSION_EXPIRED_MESSAGE` immediately —
  that message is now the terminal answer only when it's also the last
  provider tried.
- When the router had to skip past a failed provider to get an answer, it
  prefixes the returned text with a one-line note, e.g. `"⚠️ Gemini
  unavailable (quota) — answered via NVIDIA fallback.\n\n"`, so the user
  knows without needing to check logs.
- If every configured provider fails, returns the *last* provider's error
  message (so an actionable one, like the session-expired notice, still
  surfaces instead of a generic "all providers failed").
- If **no** provider is configured at all, returns a clear message telling
  the user to run `/login` or `/setnvidiakey`.

`handlers/_shared.py` constructs `ai_router = AIRouter(gemini_client,
nvidia_client)` alongside the existing singletons. `core.py`'s three call
sites (`handle_message`, `enhance_command`,
`_reply_with_gemini_image_analysis`) call `ai_router.send_message(...)` /
`ai_router.send_message_with_image(...)` instead of `gemini_client.*`
directly. `new_command` and `status_command` keep using
`gemini_client.clear_session` / `gemini_client.sessions` via the router's
passthroughs (history is stored once, on `GeminiClient`, regardless of who
answered last — see Architecture).

**Auth-gate fix (bug uncovered during this design):** `handle_message`,
`handle_photo`, `handle_image_document`, and `enhance_command` currently
gate on `auth_client.is_authenticated(user_id)` *before* ever reaching
`gemini_client` — so if Gemini OAuth is logged out but NVIDIA is configured
and would happily answer, the bot refuses the message and tells the user to
`/login`, never trying the fallback at all. These four gates change to
`ai_router.configured_providers()` being non-empty (i.e. *some* provider
can answer), not specifically "Gemini OAuth is logged in."

### Config (`config.py`)

```python
NVIDIA_API_KEY: str = ""
NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
NVIDIA_MODEL: str = "meta/llama-3.3-70b-instruct"   # solid open tool-calling model
AI_PROVIDER_ORDER: list[str] = ["gemini", "nvidia"]
```

`Config.load()` parses `AI_PROVIDER_ORDER` from a CSV env var, validates
entries against `{"gemini", "nvidia"}`, drops unknown tokens, and falls back
to the full default order if parsing leaves it empty. `Config.validate()`
does **not** hard-require `NVIDIA_API_KEY` — it's optional, same as Gemini's
API-key mode being optional today.

### Chat command: `/setnvidiakey`

New handler in `handlers/auth.py` (it's an auth-adjacent credential
command):

- `/setnvidiakey <key>` — validates it looks like `nvapi-...`, writes it to
  `~/.pdagent/config` (same INI file `configure.py` already manages,
  restricted permissions like the other credential files), calls
  `Config.load()` to pick it up immediately, confirms success, and **calls
  `context.bot.delete_message`** on the user's own message afterward so the
  raw key doesn't sit in chat history (best-effort — Telegram only allows
  deleting a user's message within 48h and if the bot has rights in that
  chat type; failure to delete is logged, not surfaced as an error).
- No args → usage help, same pattern as `/authcode`.

### Chat command: `/aiprovider`

New handler (`handlers/core.py`, alongside `/status`):

- No args — shows current order and which providers are actually usable
  right now (configured vs. not).
- With args (`/aiprovider nvidia,gemini`) — validates against
  `{"gemini", "nvidia"}`, writes `AI_PROVIDER_ORDER` to
  `~/.pdagent/config`, reloads `Config`, confirms the new order.
- Simple text-arg command rather than inline buttons — only two providers,
  a comma-separated order is unambiguous and scriptable from other tools
  the user has (e.g. a scheduled prompt), unlike `/login`'s one-shot binary
  choice which benefited from buttons.

### Setup wizard (`configure.py`)

The existing `[2/3] Gemini AI Authentication` step gets a trailing optional
sub-step: "Also configure NVIDIA NIM as a fallback? (y/N)" — if yes, prompts
for the API key and writes it plus the default `AI_PROVIDER_ORDER` alongside
the Gemini config already being written in that step.

## Data flow: fallback mid-tool-call-loop

1. `AIRouter.send_message` calls `GeminiClient`'s existing loop.
2. Turn 3 of 10: Gemini returns 429 after its own internal retries.
   `GeminiClient` already rolls back the pending turn from
   `sessions[user_id]` (existing behavior, unchanged) and returns a
   `ProviderResult(is_retryable_error=True, ...)`.
3. Router advances to `NvidiaClient`, handing it the **same**
   `sessions[user_id]` history (already rolled back to the last clean
   state by Gemini's own cleanup) plus the original user message again.
4. `NvidiaClient` runs its own turn loop from scratch against that shared
   history — tool declarations, allowlist, and dispatch are the same code
   path Gemini uses, converted at the boundary. Its successful turns are
   appended to `sessions[user_id]` in Gemini's shape via
   `openai_message_to_gemini_parts`, so the history is consistent for
   whichever provider answers the *next* message too.

## Error handling

- A provider that raises an unexpected exception (not a modeled API error)
  is treated the same as `is_retryable_error=True` — logged with
  `exc_info=True`, router moves on — so a bug in one provider's client
  degrades to "try the other one" instead of crashing the chat.
- `NVIDIA_API_KEY` present but invalid (401 from NVIDIA) is **not**
  retryable across providers in a loop sense but *is* treated as "this
  provider is down" for this message — same as Gemini's auth error — so it
  still falls through to Gemini if Gemining is configured and vice versa.
- Tool-dispatch security is unaffected: `_ALLOWED_TOOLS` enforcement lives
  in the shared `ai_tool_loop` helper both clients call, not duplicated per
  provider, so there is exactly one place that can drift.

## Testing

- `tests/test_ai_history.py` — pure-function tests for the three converters
  (round-trip a Gemini history with a tool call through to OpenAI messages
  and back; verify `tool_call_id` pairing).
- `tests/test_ai_router.py` — fake `GeminiClient`/`NvidiaClient` stand-ins
  returning canned `ProviderResult`s, asserting: order respected, skip
  unconfigured provider, fallback on retryable error, terminal error is the
  last provider's, "no provider configured" message, fallback-note
  prefixing.
- `tests/test_nvidia_client.py` — `NvidiaClient` against a mocked
  `requests`/HTTP layer (matching the existing style of Gemini's tests),
  covering: plain text response, one tool-call round trip, 429 handling,
  invalid-model error.
- Existing `GeminiClient` tests: unchanged, since its internals aren't
  touched — only the two call sites in `core.py` move to `ai_router`.

## Open items for the implementation plan (not blocking this spec)

- Exact default `NVIDIA_MODEL` — recommend `meta/llama-3.3-70b-instruct`
  (confirmed tool-calling support on build.nvidia.com as of this writing);
  the plan should re-verify current model availability/naming on
  build.nvidia.com before hardcoding, since NVIDIA's catalog changes.
- `docs/COMMANDS.md` and `README.md` command table need the two new
  commands documented (per this repo's existing convention for new
  commands).
