import os
import shutil

from src.providers import AIProvider


class ClaudeProvider(AIProvider):
    def __init__(self):
        self._path = shutil.which("claude") or "claude"
        self._model_generate = os.environ.get("AI_MODEL_GENERATE", "haiku")
        self._model_task = os.environ.get("AI_MODEL_TASK", "sonnet")

    def build_generate_command(self, role: str, salary: int, description: str) -> list[str]:
        prompt = (
            f"Generate a worker personality for a {role} with salary ${salary}. "
            f"Additional info: {description}. "
            "Include: name, emoji (single emoji for avatar), 3 personality traits, "
            "work style, favorite excuse for not working, catchphrase. "
            "Return ONLY valid JSON with keys: name, emoji, traits (array of 3 strings), "
            "catchphrase, favorite_excuse, personality_prompt (a 2-3 sentence system prompt "
            "describing this character's personality and work ethic for future interactions)."
        )
        return [self._path, "--print", "--model", self._model_generate, "--max-turns", "1", prompt]

    def build_task_command(self, personality_prompt: str, working_dir: str, message: str) -> list[str]:
        return [
            self._path, "--print",
            "--model", self._model_task,
            "--system-prompt", personality_prompt,
            "--allowedTools", "Read,Write,Edit,Glob,Grep",
            "--", message,
        ]
