"""Tests for the unified event-based middleware pipeline."""

import pytest

from src.core.action.actions import (
    BashAction, ReadAction, WriteAction, EditAction, FinishAction, GrepAction,
)
from src.core.agent.actions_result import ExecutionResult
from src.core.middleware import (
    Middleware,
    MiddlewarePipeline,
    TurnContext,
    ActionCallContext,
    PermissionMiddleware,
    OutputTruncationMiddleware,
    TimingMiddleware,
    AuditLogMiddleware,
    TurnLoggingMiddleware,
    TokenBudgetMiddleware,
    ErrorRecoveryMiddleware,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok_handler(action):
    """Simulates a successful action handler."""
    return f"<output>result for {type(action).__name__}</output>", False


def _error_handler(action):
    return "<output>[ERROR] something failed</output>", True


def _large_output_handler(action):
    return "x" * 100_000, False


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


# ===================================================================
# Action-level middleware tests
# ===================================================================

class TestActionPipeline:

    def test_empty_pipeline_calls_handler_directly(self):
        pipeline = MiddlewarePipeline([])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert "BashAction" in output
        assert is_error is False

    def test_single_middleware_wraps_handler(self):
        calls = []

        class TrackerMW(Middleware):
            def before_action_call(self, ctx):
                calls.append("before")
                return ctx
            def after_action_call(self, ctx):
                calls.append("after")
                return ctx

        pipeline = MiddlewarePipeline([TrackerMW()])
        pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert calls == ["before", "after"]

    def test_middleware_ordering_is_outermost_first(self):
        order = []

        class MW(Middleware):
            def __init__(self, name):
                self._name = name
            def before_action_call(self, ctx):
                order.append(f"{self._name}_pre")
                return ctx
            def after_action_call(self, ctx):
                order.append(f"{self._name}_post")
                return ctx

        pipeline = MiddlewarePipeline([MW("A"), MW("B"), MW("C")])
        pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert order == ["A_pre", "B_pre", "C_pre", "C_post", "B_post", "A_post"]

    def test_middleware_can_short_circuit(self):
        class BlockMW(Middleware):
            def before_action_call(self, ctx):
                ctx.output = "blocked"
                ctx.is_error = True
                ctx.skipped = True
                return ctx

        pipeline = MiddlewarePipeline([BlockMW()])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert output == "blocked"
        assert is_error is True


class TestPermissionMiddleware:

    def test_allows_permitted_action(self):
        mw = PermissionMiddleware(
            allowed_actions={BashAction, ReadAction},
            agent_name="explorer",
        )
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert is_error is False
        assert "BashAction" in output

    def test_blocks_disallowed_action(self):
        mw = PermissionMiddleware(
            allowed_actions={ReadAction, GrepAction},
            agent_name="explorer",
        )
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(
            WriteAction(file_path="/tmp/f", content="x"), _ok_handler
        )
        assert is_error is True
        assert "PERMISSION DENIED" in output
        assert "explorer" in output
        assert "WriteAction" in output

    def test_blocks_edit_for_explorer(self):
        mw = PermissionMiddleware(
            allowed_actions={ReadAction, BashAction},
            agent_name="explorer",
        )
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(
            EditAction(file_path="/f", old_string="a", new_string="b"),
            _ok_handler,
        )
        assert is_error is True
        assert "PERMISSION DENIED" in output

    def test_allows_all_when_full_set(self):
        all_types = {BashAction, ReadAction, WriteAction, EditAction, FinishAction}
        mw = PermissionMiddleware(allowed_actions=all_types, agent_name="coder")
        pipeline = MiddlewarePipeline([mw])

        for action_cls, kwargs in [
            (BashAction, {"cmd": "ls"}),
            (ReadAction, {"file_path": "/f"}),
            (WriteAction, {"file_path": "/f", "content": "x"}),
            (FinishAction, {"message": "done"}),
        ]:
            action = action_cls(**kwargs)
            _, is_error = pipeline.execute_action(action, _ok_handler)
            assert is_error is False, f"{action_cls.__name__} should be allowed"


class TestOutputTruncationMiddleware:

    def test_passes_short_output_unchanged(self):
        mw = OutputTruncationMiddleware(max_chars=1000)
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert is_error is False
        assert "TRUNCATED" not in output

    def test_truncates_long_output(self):
        mw = OutputTruncationMiddleware(max_chars=500)
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _large_output_handler)
        assert is_error is False
        assert len(output) < 100_000
        assert "TRUNCATED" in output
        assert "99500 chars removed" in output

    def test_preserves_error_flag(self):
        mw = OutputTruncationMiddleware(max_chars=10)
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _error_handler)
        assert is_error is True

    def test_exact_boundary_not_truncated(self):
        def exact_handler(action):
            return "x" * 100, False

        mw = OutputTruncationMiddleware(max_chars=100)
        pipeline = MiddlewarePipeline([mw])
        output, _ = pipeline.execute_action(BashAction(cmd="ls"), exact_handler)
        assert "TRUNCATED" not in output
        assert len(output) == 100

    def test_one_over_boundary_is_truncated(self):
        def over_handler(action):
            return "x" * 101, False

        mw = OutputTruncationMiddleware(max_chars=100)
        pipeline = MiddlewarePipeline([mw])
        output, _ = pipeline.execute_action(BashAction(cmd="ls"), over_handler)
        assert "TRUNCATED" in output


class TestTimingMiddleware:

    def test_passes_through_result(self):
        mw = TimingMiddleware()
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert "BashAction" in output
        assert is_error is False

    def test_passes_through_error(self):
        mw = TimingMiddleware()
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _error_handler)
        assert is_error is True


class TestAuditLogMiddleware:

    def test_passes_through_result(self):
        mw = AuditLogMiddleware(agent_name="coder")
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(ReadAction(file_path="/f"), _ok_handler)
        assert "ReadAction" in output
        assert is_error is False

    def test_passes_through_error(self):
        mw = AuditLogMiddleware(agent_name="coder")
        pipeline = MiddlewarePipeline([mw])
        output, is_error = pipeline.execute_action(BashAction(cmd="fail"), _error_handler)
        assert is_error is True


class TestActionHandlerWithMiddleware:
    """Integration: ActionHandler + middleware pipeline end-to-end."""

    def test_action_handler_uses_middleware(self):
        from src.core.agent.action_handler import ActionHandler

        handler = ActionHandler(
            actions={BashAction: _ok_handler},
            agent_name="test",
            middlewares=[OutputTruncationMiddleware(max_chars=50)],
        )

        result = handler.execute("""<bash>
cmd: "echo hello"
</bash>""")

        assert len(result.actions_executed) == 1
        assert not result.has_error

    def test_permission_middleware_blocks_in_handler(self):
        from src.core.agent.action_handler import ActionHandler

        handler = ActionHandler(
            actions={
                WriteAction: _ok_handler,
                ReadAction: _ok_handler,
            },
            agent_name="explorer",
            middlewares=[
                PermissionMiddleware(
                    allowed_actions={ReadAction},
                    agent_name="explorer",
                ),
            ],
        )

        result = handler.execute("""<file>
action: write
file_path: "/tmp/bad"
content: "should be blocked"
</file>""")

        assert len(result.actions_executed) == 1
        assert result.has_error is True
        assert "PERMISSION DENIED" in result.env_responses[0]


class TestFullActionPipelineIntegration:

    def test_full_stack_happy_path(self):
        pipeline = MiddlewarePipeline([
            AuditLogMiddleware(agent_name="coder"),
            TimingMiddleware(),
            PermissionMiddleware(allowed_actions={BashAction, ReadAction}, agent_name="coder"),
            OutputTruncationMiddleware(max_chars=50_000),
        ])
        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert is_error is False
        assert "BashAction" in output

    def test_permission_short_circuits_before_timing_and_truncation(self):
        call_order = []

        class TrackingTruncation(Middleware):
            def after_action_call(self, ctx):
                call_order.append("truncation")
                return ctx

        pipeline = MiddlewarePipeline([
            PermissionMiddleware(allowed_actions={ReadAction}, agent_name="explorer"),
            TrackingTruncation(),
        ])
        output, is_error = pipeline.execute_action(
            WriteAction(file_path="/f", content="x"), _ok_handler
        )
        assert is_error is True
        assert "PERMISSION DENIED" in output
        assert call_order == []


# ===================================================================
# Turn-level middleware tests
# ===================================================================

class TestTurnPipeline:

    def test_empty_pipeline_calls_core(self):
        pipeline = MiddlewarePipeline([])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _identity_core)
        assert ctx.result is not None
        assert ctx.result.env_responses == ["ok"]

    def test_single_middleware_wraps_core(self):
        calls = []

        class TrackerMiddleware(Middleware):
            def before_turn(self, ctx):
                calls.append("before")
                return ctx
            def after_turn(self, ctx):
                calls.append("after")
                return ctx

        pipeline = MiddlewarePipeline([TrackerMiddleware()])
        ctx = _make_ctx()
        pipeline.execute_turn(ctx, _identity_core)
        assert calls == ["before", "after"]

    def test_middleware_ordering_is_outermost_first(self):
        order = []

        class MW(Middleware):
            def __init__(self, name):
                self.name = name
            def before_turn(self, ctx):
                order.append(f"{self.name}_pre")
                return ctx
            def after_turn(self, ctx):
                order.append(f"{self.name}_post")
                return ctx

        pipeline = MiddlewarePipeline([MW("A"), MW("B"), MW("C")])
        pipeline.execute_turn(_make_ctx(), _identity_core)
        assert order == ["A_pre", "B_pre", "C_pre", "C_post", "B_post", "A_post"]

    def test_middleware_can_abort_without_calling_next(self):
        class AbortMiddleware(Middleware):
            def before_turn(self, ctx):
                ctx.aborted = True
                ctx.abort_reason = "stopped"
                return ctx

        pipeline = MiddlewarePipeline([AbortMiddleware()])
        ctx = pipeline.execute_turn(_make_ctx(), _identity_core)
        assert ctx.aborted is True
        assert ctx.result is None


class TestTurnLoggingMiddleware:

    def test_records_duration_in_metadata(self):
        pipeline = MiddlewarePipeline([TurnLoggingMiddleware()])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _identity_core)
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

        pipeline = MiddlewarePipeline([TurnLoggingMiddleware()])
        ctx = pipeline.execute_turn(_make_ctx(), finishing_core)
        assert ctx.result.done is True


class TestTokenBudgetMiddleware:

    def test_allows_turn_under_budget(self):
        pipeline = MiddlewarePipeline([TokenBudgetMiddleware(max_tokens=999_999)])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _identity_core)
        assert ctx.aborted is False
        assert ctx.result is not None

    def test_aborts_turn_over_budget(self):
        pipeline = MiddlewarePipeline([TokenBudgetMiddleware(max_tokens=1)])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _identity_core)
        assert ctx.aborted is True
        assert "Token budget exceeded" in ctx.abort_reason
        assert ctx.result is None

    def test_records_token_count_in_metadata(self):
        pipeline = MiddlewarePipeline([TokenBudgetMiddleware(max_tokens=999_999)])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _identity_core)
        assert "pre_turn_token_count" in ctx.metadata


class TestErrorRecoveryMiddleware:

    def test_passes_through_on_success(self):
        pipeline = MiddlewarePipeline([ErrorRecoveryMiddleware()])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _identity_core)
        assert ctx.result.has_error is False
        assert "turn_error" not in ctx.metadata

    def test_catches_exception_and_creates_error_result(self):
        pipeline = MiddlewarePipeline([ErrorRecoveryMiddleware()])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _failing_core)
        assert ctx.result is not None
        assert ctx.result.has_error is True
        assert "[ERROR] Turn failed: boom" in ctx.result.env_responses[0]
        assert ctx.metadata["turn_error"] == "boom"

    def test_does_not_abort(self):
        pipeline = MiddlewarePipeline([ErrorRecoveryMiddleware()])
        ctx = _make_ctx()
        ctx = pipeline.execute_turn(ctx, _failing_core)
        assert ctx.aborted is False


class TestFullTurnPipelineIntegration:

    def test_logging_plus_error_recovery(self):
        pipeline = MiddlewarePipeline([
            TurnLoggingMiddleware(),
            ErrorRecoveryMiddleware(),
        ])
        ctx = pipeline.execute_turn(_make_ctx(), _failing_core)
        assert ctx.result.has_error is True
        assert "turn_duration_secs" in ctx.metadata
        assert "turn_error" in ctx.metadata

    def test_token_budget_short_circuits_before_core(self):
        core_called = []

        def tracking_core(ctx):
            core_called.append(True)
            return _identity_core(ctx)

        pipeline = MiddlewarePipeline([
            TurnLoggingMiddleware(),
            ErrorRecoveryMiddleware(),
            TokenBudgetMiddleware(max_tokens=1),
        ])
        ctx = pipeline.execute_turn(_make_ctx(), tracking_core)
        assert ctx.aborted is True
        assert not core_called

    def test_full_stack_happy_path(self):
        pipeline = MiddlewarePipeline([
            TurnLoggingMiddleware(),
            ErrorRecoveryMiddleware(),
            TokenBudgetMiddleware(max_tokens=999_999),
        ])
        ctx = pipeline.execute_turn(_make_ctx(), _identity_core)
        assert ctx.result is not None
        assert ctx.result.has_error is False
        assert not ctx.aborted
        assert "turn_duration_secs" in ctx.metadata
        assert "pre_turn_token_count" in ctx.metadata


# ===================================================================
# Cross-cutting: single middleware handling both turn and action events
# ===================================================================

class TestUnifiedMiddleware:

    def test_single_middleware_handles_both_turn_and_action_events(self):
        events = []

        class FullLifecycleMiddleware(Middleware):
            def before_turn(self, ctx):
                events.append("before_turn")
                return ctx
            def after_turn(self, ctx):
                events.append("after_turn")
                return ctx
            def before_action_call(self, ctx):
                events.append("before_action_call")
                return ctx
            def after_action_call(self, ctx):
                events.append("after_action_call")
                return ctx

        mw = FullLifecycleMiddleware()
        pipeline = MiddlewarePipeline([mw])

        pipeline.execute_turn(_make_ctx(), _identity_core)
        assert events == ["before_turn", "after_turn"]

        events.clear()
        pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert events == ["before_action_call", "after_action_call"]

    def test_default_middleware_is_noop(self):
        pipeline = MiddlewarePipeline([Middleware()])

        ctx = pipeline.execute_turn(_make_ctx(), _identity_core)
        assert ctx.result is not None

        output, is_error = pipeline.execute_action(BashAction(cmd="ls"), _ok_handler)
        assert "BashAction" in output
        assert is_error is False
