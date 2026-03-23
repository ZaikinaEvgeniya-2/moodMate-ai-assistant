import os
import pytest
from unittest.mock import patch

from src.providers import AIProvider, get_provider
from src.providers.claude_provider import ClaudeProvider
from src.providers.opencode_provider import OpencodeProvider
from src.worker import Worker


class TestGetProvider:
    def test_default_returns_opencode(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AI_PROVIDER", None)
            provider = get_provider()
            assert isinstance(provider, OpencodeProvider)

    def test_claude_env_returns_claude(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "claude"}):
            provider = get_provider()
            assert isinstance(provider, ClaudeProvider)

    def test_opencode_env_returns_opencode(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "opencode"}):
            provider = get_provider()
            assert isinstance(provider, OpencodeProvider)

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"AI_PROVIDER": "Claude"}):
            provider = get_provider()
            assert isinstance(provider, ClaudeProvider)


class TestClaudeProvider:
    def test_build_generate_command(self):
        provider = ClaudeProvider()
        cmd = provider.build_generate_command(role="developer", salary=1200, description="good at Python")
        assert cmd[0].endswith("claude") or "claude" in cmd[0]
        assert "--print" in cmd
        assert "--model" in cmd
        assert "haiku" in cmd
        prompt = cmd[-1]
        assert "developer" in prompt
        assert "1200" in prompt
        assert "good at Python" in prompt

    def test_build_generate_command_custom_model(self):
        with patch.dict(os.environ, {"AI_MODEL_GENERATE": "opus"}):
            provider = ClaudeProvider()
            cmd = provider.build_generate_command(role="dev", salary=500, description="")
            assert "opus" in cmd

    def test_build_task_command(self):
        provider = ClaudeProvider()
        cmd = provider.build_task_command(
            personality_prompt="You are Alex, a hard worker.",
            working_dir="/tmp/test_worker",
            message="Fix the login bug",
        )
        assert "--print" in cmd
        assert "--system-prompt" in cmd
        idx = cmd.index("--system-prompt")
        assert cmd[idx + 1] == "You are Alex, a hard worker."
        assert "--allowedTools" in cmd
        assert "--working-dir" in cmd
        idx = cmd.index("--working-dir")
        assert cmd[idx + 1] == "/tmp/test_worker"
        assert cmd[-1] == "Fix the login bug"

    def test_build_task_command_custom_model(self):
        with patch.dict(os.environ, {"AI_MODEL_TASK": "opus"}):
            provider = ClaudeProvider()
            cmd = provider.build_task_command(
                personality_prompt="Test", working_dir="/tmp", message="Do stuff",
            )
            assert "opus" in cmd


class TestOpencodeProvider:
    def test_build_generate_command(self):
        provider = OpencodeProvider()
        cmd = provider.build_generate_command(role="writer", salary=800, description="loves poetry")
        assert "opencode" in cmd[0]
        assert "run" in cmd
        assert "-m" in cmd
        prompt = cmd[-1]
        assert "writer" in prompt
        assert "800" in prompt
        assert "loves poetry" in prompt

    def test_build_generate_command_custom_model(self):
        with patch.dict(os.environ, {"AI_MODEL_GENERATE": "opencode/llama-fast"}):
            provider = OpencodeProvider()
            cmd = provider.build_generate_command(role="dev", salary=500, description="")
            assert "opencode/llama-fast" in cmd

    def test_build_generate_command_no_system_prompt_flag(self):
        provider = OpencodeProvider()
        cmd = provider.build_generate_command(role="dev", salary=500, description="")
        assert "--system-prompt" not in cmd

    def test_build_task_command(self):
        provider = OpencodeProvider()
        cmd = provider.build_task_command(
            personality_prompt="You are grumpy Bob.",
            working_dir="/tmp/workspace",
            message="Write tests",
        )
        assert "run" in cmd
        assert "--dir" in cmd
        idx = cmd.index("--dir")
        assert cmd[idx + 1] == "/tmp/workspace"
        # Personality is embedded in the message
        combined = cmd[-1]
        assert "You are grumpy Bob." in combined
        assert "Write tests" in combined

    def test_build_task_command_custom_model(self):
        with patch.dict(os.environ, {"AI_MODEL_TASK": "opencode/gpt-4o"}):
            provider = OpencodeProvider()
            cmd = provider.build_task_command(
                personality_prompt="Test", working_dir="/tmp", message="Do stuff",
            )
            assert "opencode/gpt-4o" in cmd

    def test_build_task_command_no_system_prompt_flag(self):
        provider = OpencodeProvider()
        cmd = provider.build_task_command(
            personality_prompt="Test",
            working_dir="/tmp",
            message="Do stuff",
        )
        assert "--system-prompt" not in cmd
        assert "--allowedTools" not in cmd


class TestWorker:
    def test_working_dir_round_trip(self):
        worker = Worker(
            name="Alice", emoji="👩", role="developer", salary=1000,
            personality_prompt="prompt", traits=["smart"],
            catchphrase="hi", favorite_excuse="busy",
            working_dir="/home/user/project",
        )
        data = worker.to_dict()
        assert data["working_dir"] == "/home/user/project"

        restored = Worker.from_dict(data)
        assert restored.working_dir == "/home/user/project"

    def test_working_dir_defaults_empty(self):
        worker = Worker(
            name="Bob", emoji="👨", role="tester", salary=500,
            personality_prompt="prompt", traits=["calm"],
            catchphrase="ok", favorite_excuse="later",
        )
        assert worker.working_dir == ""

        data = worker.to_dict()
        restored = Worker.from_dict(data)
        assert restored.working_dir == ""

    def test_from_dict_missing_working_dir(self):
        """Existing workers saved without working_dir should load fine."""
        data = {
            "name": "Old", "emoji": "🧓", "role": "writer", "salary": 300,
            "personality_prompt": "p", "traits": [], "catchphrase": "c",
            "favorite_excuse": "e",
        }
        worker = Worker.from_dict(data)
        assert worker.working_dir == ""
