import os
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for AI CLI providers."""

    @abstractmethod
    def build_generate_command(self, role: str, salary: int, description: str) -> list[str]:
        """Build CLI command for personality generation."""
        ...

    @abstractmethod
    def build_task_command(self, personality_prompt: str, working_dir: str, message: str) -> list[str]:
        """Build CLI command for task execution."""
        ...

    @abstractmethod
    def build_conversation_command(self, personality_a: str, name_a: str,
                                    personality_b: str, name_b: str) -> list[str]:
        """Build CLI command for generating a friend conversation."""
        ...


def get_provider() -> AIProvider:
    """Return provider based on AI_PROVIDER env var. Default: opencode."""
    name = os.environ.get("AI_PROVIDER", "opencode").lower()
    if name == "claude":
        from src.providers.claude_provider import ClaudeProvider
        return ClaudeProvider()
    else:
        from src.providers.opencode_provider import OpencodeProvider
        return OpencodeProvider()
