"""Tests for the turn middleware pipeline."""

import pytest

from src.core.agent.actions_result import ExecutionResult
from src.core.agent.turn_middleware import (
    TurnContext,
    TurnMiddleware,
    TurnPipeline,
    TurnLoggingMiddleware,
    TokenBudgetMiddleware,
    ErrorRecoveryMiddleware,
)


def _make_ctx(**overrides) -> TurnContext:
    defaults = dict(
        agent_name="test_agent",
        turn_num=1,
        max_turns=10,
        messages=[{"role": "system", "content": "hi"}],
    )
    defaults.update(overrides)
    return TurnContext(**defaults)


def _identity_core(ctx: TurnContext) -> TurnContext:
    ctx.result = ExecutionResult(
        actions_executed=[],
        env_responses=["ok"],
        has_error=False,
        done=False,
    )
    return ctx


def _failing_core(ctx: TurnContext) -> TurnContext:
    raise RuntimeError("boom")


class TestTurnPipeline:

    def test_empty_pipeline_calls_core(self):
        pipeline = TurnPipeline([])
        ctx = _make_ctx()
        ctx = pipeline.execute(ctx, _identity_core)
        assert ctx.result is not None
        assert ctx.result.env_responses == ["ok"]

    def test_single_middleware_wraps_core(self):
        calls = []

        class TrackerMiddleware(TurnMiddleware):
            def __call__(self, ctx, next_call):
                calls.append("before")
                ctx = next_call(ctx)
                calls.append("after")
                return ctx

        pipeline = TurnPipeline([TrackerMiddleware()])
        ctx = _make_ctx()
        pipeline.execute(ctx, _identity_core)
        assert calls == ["before", "after"]

    def test_middleware_ordering_is_outermost_first(self):
        order = []

        class MW(TurnMiddleware):
            def __init__(self, name):
                self.name = name
            def __call__(self, ctx, next_call):
                order.append(f"{self.name}_pre")
                ctx = next_call(ctx)
                order.append(f"{self.name}_post")
                return ctx

        pipeline = TurnPipeline([MW("A"), MW("B"), MW("C")])
        pipeline.execute(_make_ctx(), _identity_core)
        assert order == ["A_pre", "B_pre", "C_pre", "C_post", "B_post", "A_post"]

    def test_middleware_can_abort_without_calling_next(self):
        class AbortMiddleware(TurnMiddleware):
            def __call__(self, ctx, next_call):
                ctx.aborted = True
                ctx.abort_reason = "stopped"
                return ctx

        pipeline = TurnPipeline([AbortMiddleware()])
        ctx = pipeline.execute(_make_ctx(), _identity_core)
        assert ctx.aborted is True
        assert ctx.result is None


class TestTurnLoggingMiddleware:

    def test_records_duration_in_metadata(self):
        mw = TurnLoggingMiddleware()
        ctx = _make_ctx()
        ctx = mw(ctx, _identity_core)
        assert "turn_duration_secs" in ctx.metadata
        assert ctx.metadata["turn_duration_secs"] >= 0

    def test_logs_finished_turn(self):
        def finishing_core(ctx):
            ctx.result = ExecutionResult(
                actions_executed=[],
                env_responses=[],
                has_error=False,
                done=True,
                finish_message="all done",
            )
            return ctx

        mw = TurnLoggingMiddleware()
        ctx = mw(_make_ctx(), finishing_core)
        assert ctx.result.done is True


class TestTokenBudgetMiddleware:

    def test_allows_turn_under_budget(self):
        mw = TokenBudgetMiddleware(max_tokens=999_999)
        ctx = _make_ctx()
        ctx = mw(ctx, _identity_core)
        assert ctx.aborted is False
        assert ctx.result is not None

    def test_aborts_turn_over_budget(self):
        mw = TokenBudgetMiddleware(max_tokens=1)
        ctx = _make_ctx()
        ctx = mw(ctx, _identity_core)
        assert ctx.aborted is True
        assert "Token budget exceeded" in ctx.abort_reason
        assert ctx.result is None

    def test_records_token_count_in_metadata(self):
        mw = TokenBudgetMiddleware(max_tokens=999_999)
        ctx = _make_ctx()
        ctx = mw(ctx, _identity_core)
        assert "pre_turn_token_count" in ctx.metadata


class TestErrorRecoveryMiddleware:

    def test_passes_through_on_success(self):
        mw = ErrorRecoveryMiddleware()
        ctx = _make_ctx()
        ctx = mw(ctx, _identity_core)
        assert ctx.result.has_error is False
        assert "turn_error" not in ctx.metadata

    def test_catches_exception_and_creates_error_result(self):
        mw = ErrorRecoveryMiddleware()
        ctx = _make_ctx()
        ctx = mw(ctx, _failing_core)
        assert ctx.result is not None
        assert ctx.result.has_error is True
        assert "[ERROR] Turn failed: boom" in ctx.result.env_responses[0]
        assert ctx.metadata["turn_error"] == "boom"

    def test_does_not_abort(self):
        mw = ErrorRecoveryMiddleware()
        ctx = _make_ctx()
        ctx = mw(ctx, _failing_core)
        assert ctx.aborted is False


class TestFullPipelineIntegration:

    def test_logging_plus_error_recovery(self):
        pipeline = TurnPipeline([
            TurnLoggingMiddleware(),
            ErrorRecoveryMiddleware(),
        ])
        ctx = pipeline.execute(_make_ctx(), _failing_core)
        assert ctx.result.has_error is True
        assert "turn_duration_secs" in ctx.metadata
        assert "turn_error" in ctx.metadata

    def test_token_budget_short_circuits_before_core(self):
        core_called = []

        def tracking_core(ctx):
            core_called.append(True)
            return _identity_core(ctx)

        pipeline = TurnPipeline([
            TurnLoggingMiddleware(),
            ErrorRecoveryMiddleware(),
            TokenBudgetMiddleware(max_tokens=1),
        ])
        ctx = pipeline.execute(_make_ctx(), tracking_core)
        assert ctx.aborted is True
        assert not core_called

    def test_full_stack_happy_path(self):
        pipeline = TurnPipeline([
            TurnLoggingMiddleware(),
            ErrorRecoveryMiddleware(),
            TokenBudgetMiddleware(max_tokens=999_999),
        ])
        ctx = pipeline.execute(_make_ctx(), _identity_core)
        assert ctx.result is not None
        assert ctx.result.has_error is False
        assert not ctx.aborted
        assert "turn_duration_secs" in ctx.metadata
        assert "pre_turn_token_count" in ctx.metadata
