from unittest.mock import patch, MagicMock

from src.ai_engine import AIEngine


def test_engine_uses_provider():
    """AIEngine delegates command building to its provider."""
    engine = AIEngine()
    assert hasattr(engine._provider, "build_generate_command")
    assert hasattr(engine._provider, "build_task_command")


def test_engine_provider_from_env():
    """AI_PROVIDER env var controls which provider is used."""
    with patch.dict("os.environ", {"AI_PROVIDER": "claude"}):
        from src.providers.claude_provider import ClaudeProvider
        engine = AIEngine()
        assert isinstance(engine._provider, ClaudeProvider)


def test_is_worker_busy_default_false():
    engine = AIEngine()
    assert engine.is_worker_busy("nonexistent") is False
