import pytest
from unittest.mock import MagicMock, patch
from src.ai_engine import AIEngine


def test_build_generate_command():
    engine = AIEngine()
    cmd = engine._build_generate_command(role="developer", salary=1200, description="good at Python")
    assert "claude" in cmd[0] or cmd[0].endswith("claude")
    assert "--print" in cmd
    prompt_arg = cmd[-1]
    assert "developer" in prompt_arg
    assert "1200" in prompt_arg
    assert "good at Python" in prompt_arg


def test_build_task_command():
    engine = AIEngine()
    cmd = engine._build_task_command(
        personality_prompt="You are Alex, a hard worker.",
        working_dir="/tmp/test_worker",
        message="Fix the login bug",
    )
    assert "--print" in cmd
    assert "--system-prompt" in cmd
    prompt_idx = cmd.index("--system-prompt")
    assert cmd[prompt_idx + 1] == "You are Alex, a hard worker."
    assert "Fix the login bug" in cmd[-1]


def test_build_task_command_includes_allowedtools():
    engine = AIEngine()
    cmd = engine._build_task_command(
        personality_prompt="You are Alex.",
        working_dir="/tmp/test",
        message="Do something",
    )
    assert "--allowedTools" in cmd
