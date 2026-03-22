# Context Module Implementation

✅ Simple - Single-pass executable, low risk

## Steps

- [x] 1. Create `src/core/context/context.py` — `Context` dataclass with `to_dict()` method
- [x] 2. Create `src/core/context/context_store.py` — `ContextStore` in-memory key-value store
- [x] 3. Create `src/core/context/__init__.py` — Public API re-exporting `Context` and `ContextStore`
- [x] 4. Create `src/core/context/context_handler.py` — `AddContextActionHandler` with dedup logic
- [x] 5. Validate: run existing tests / import check to ensure no errors
