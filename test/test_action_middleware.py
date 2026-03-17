"""Tests for the action middleware pipeline."""

import pytest

from src.core.action.actions import (
    BashAction, ReadAction, WriteAction, EditAction, FinishAction, GrepAction,
)
from src.core.action.middleware import (
    ActionMiddleware,
    ActionPipeline,
    PermissionMiddleware,
    OutputTruncationMiddleware,
    TimingMiddleware,
    AuditLogMiddleware,
)


def _ok_handler(action):
    """Simulates a successful action handler."""
    return f"<output>result for {type(action).__name__}</output>", False


def _error_handler(action):
    return "<output>[ERROR] something failed</output>", True


def _large_output_handler(action):
    return "x" * 100_000, False


class TestActionPipeline:

    def test_empty_pipeline_calls_handler_directly(self):
        pipeline = ActionPipeline([])
        wrapped = pipeline.wrap(_ok_handler)
        output, is_error = wrapped(BashAction(cmd="ls"))
        assert "BashAction" in output
        assert is_error is False

    def test_single_middleware_wraps_handler(self):
        calls = []

        class TrackerMW(ActionMiddleware):
            def __call__(self, action, next_call):
                calls.append("before")
                result = next_call(action)
                calls.append("after")
                return result

        pipeline = ActionPipeline([TrackerMW()])
        wrapped = pipeline.wrap(_ok_handler)
        wrapped(BashAction(cmd="ls"))
        assert calls == ["before", "after"]

    def test_middleware_ordering_is_outermost_first(self):
        order = []

        class MW(ActionMiddleware):
            def __init__(self, name):
                self._name = name
            def __call__(self, action, next_call):
                order.append(f"{self._name}_pre")
                result = next_call(action)
                order.append(f"{self._name}_post")
                return result

        pipeline = ActionPipeline([MW("A"), MW("B"), MW("C")])
        wrapped = pipeline.wrap(_ok_handler)
        wrapped(BashAction(cmd="ls"))
        assert order == ["A_pre", "B_pre", "C_pre", "C_post", "B_post", "A_post"]

    def test_middleware_can_short_circuit(self):
        class BlockMW(ActionMiddleware):
            def __call__(self, action, next_call):
                return "blocked", True

        pipeline = ActionPipeline([BlockMW()])
        wrapped = pipeline.wrap(_ok_handler)
        output, is_error = wrapped(BashAction(cmd="ls"))
        assert output == "blocked"
        assert is_error is True


class TestPermissionMiddleware:

    def test_allows_permitted_action(self):
        mw = PermissionMiddleware(
            allowed_actions={BashAction, ReadAction},
            agent_name="explorer",
        )
        output, is_error = mw(BashAction(cmd="ls"), _ok_handler)
        assert is_error is False
        assert "BashAction" in output

    def test_blocks_disallowed_action(self):
        mw = PermissionMiddleware(
            allowed_actions={ReadAction, GrepAction},
            agent_name="explorer",
        )
        output, is_error = mw(WriteAction(file_path="/tmp/f", content="x"), _ok_handler)
        assert is_error is True
        assert "PERMISSION DENIED" in output
        assert "explorer" in output
        assert "WriteAction" in output

    def test_blocks_edit_for_explorer(self):
        mw = PermissionMiddleware(
            allowed_actions={ReadAction, BashAction},
            agent_name="explorer",
        )
        output, is_error = mw(
            EditAction(file_path="/f", old_string="a", new_string="b"),
            _ok_handler,
        )
        assert is_error is True
        assert "PERMISSION DENIED" in output

    def test_allows_all_when_full_set(self):
        all_types = {BashAction, ReadAction, WriteAction, EditAction, FinishAction}
        mw = PermissionMiddleware(allowed_actions=all_types, agent_name="coder")

        for action_cls, kwargs in [
            (BashAction, {"cmd": "ls"}),
            (ReadAction, {"file_path": "/f"}),
            (WriteAction, {"file_path": "/f", "content": "x"}),
            (FinishAction, {"message": "done"}),
        ]:
            action = action_cls(**kwargs)
            _, is_error = mw(action, _ok_handler)
            assert is_error is False, f"{action_cls.__name__} should be allowed"


class TestOutputTruncationMiddleware:

    def test_passes_short_output_unchanged(self):
        mw = OutputTruncationMiddleware(max_chars=1000)
        output, is_error = mw(BashAction(cmd="ls"), _ok_handler)
        assert is_error is False
        assert "TRUNCATED" not in output

    def test_truncates_long_output(self):
        mw = OutputTruncationMiddleware(max_chars=500)
        output, is_error = mw(BashAction(cmd="ls"), _large_output_handler)
        assert is_error is False
        assert len(output) < 100_000
        assert "TRUNCATED" in output
        assert "99500 chars removed" in output

    def test_preserves_error_flag(self):
        mw = OutputTruncationMiddleware(max_chars=10)
        output, is_error = mw(BashAction(cmd="ls"), _error_handler)
        assert is_error is True

    def test_exact_boundary_not_truncated(self):
        def exact_handler(action):
            return "x" * 100, False

        mw = OutputTruncationMiddleware(max_chars=100)
        output, _ = mw(BashAction(cmd="ls"), exact_handler)
        assert "TRUNCATED" not in output
        assert len(output) == 100

    def test_one_over_boundary_is_truncated(self):
        def over_handler(action):
            return "x" * 101, False

        mw = OutputTruncationMiddleware(max_chars=100)
        output, _ = mw(BashAction(cmd="ls"), over_handler)
        assert "TRUNCATED" in output


class TestTimingMiddleware:

    def test_passes_through_result(self):
        mw = TimingMiddleware()
        output, is_error = mw(BashAction(cmd="ls"), _ok_handler)
        assert "BashAction" in output
        assert is_error is False

    def test_passes_through_error(self):
        mw = TimingMiddleware()
        output, is_error = mw(BashAction(cmd="ls"), _error_handler)
        assert is_error is True


class TestAuditLogMiddleware:

    def test_passes_through_result(self):
        mw = AuditLogMiddleware(agent_name="coder")
        output, is_error = mw(ReadAction(file_path="/f"), _ok_handler)
        assert "ReadAction" in output
        assert is_error is False

    def test_passes_through_error(self):
        mw = AuditLogMiddleware(agent_name="coder")
        output, is_error = mw(BashAction(cmd="fail"), _error_handler)
        assert is_error is True


class TestActionHandlerWithMiddleware:
    """Integration: ActionHandler + middleware pipeline end-to-end."""

    def test_action_handler_uses_middleware(self):
        from src.core.agent.action_handler import ActionHandler

        handler = ActionHandler(
            actions={BashAction: _ok_handler},
            agent_name="test",
            action_middlewares=[OutputTruncationMiddleware(max_chars=50)],
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
            action_middlewares=[
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


class TestFullPipelineIntegration:

    def test_full_stack_happy_path(self):
        pipeline = ActionPipeline([
            AuditLogMiddleware(agent_name="coder"),
            TimingMiddleware(),
            PermissionMiddleware(allowed_actions={BashAction, ReadAction}, agent_name="coder"),
            OutputTruncationMiddleware(max_chars=50_000),
        ])
        wrapped = pipeline.wrap(_ok_handler)
        output, is_error = wrapped(BashAction(cmd="ls"))
        assert is_error is False
        assert "BashAction" in output

    def test_permission_short_circuits_before_timing_and_truncation(self):
        call_order = []

        class TrackingTruncation(ActionMiddleware):
            def __call__(self, action, next_call):
                call_order.append("truncation")
                return next_call(action)

        pipeline = ActionPipeline([
            PermissionMiddleware(allowed_actions={ReadAction}, agent_name="explorer"),
            TrackingTruncation(),
        ])
        wrapped = pipeline.wrap(_ok_handler)
        output, is_error = wrapped(WriteAction(file_path="/f", content="x"))
        assert is_error is True
        assert "PERMISSION DENIED" in output
        assert call_order == []
