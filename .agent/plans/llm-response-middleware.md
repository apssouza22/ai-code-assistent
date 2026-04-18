**Complexity:** ✅ Simple — single-pass executable, low risk

## Goal

Extract `handle_llm_response` / `_execute_tools` from `Agent` into a dedicated middleware + pipeline phase so other middlewares can observe or short-circuit LLM-response handling.

## Steps

- [x] Extend `TurnContext` with `llm_response_handling_skipped`; extend `Middleware` with `before_llm_response_handling` / `after_llm_response_handling`; add `execute_llm_response` to `MiddlewarePipeline`.
  - **Validation:** Run existing tests / import smoke check.

- [x] Add `LlmResponseToolMiddleware` (tool parsing + pipeline-wrapped action execution), bind pipeline after `MiddlewarePipeline` construction; wire `Agent._turn` to use `execute_llm_response`.
  - **Validation:** `python -m pytest` (or project test command) if present; minimal script import.

- [x] Export new middleware from `src/core/middleware/__init__.py`; update `docs/middleware-for-ai-agents.md` if it documents hooks.
  - **Validation:** Grep for broken imports.
