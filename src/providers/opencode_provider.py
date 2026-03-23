import shutil

from src.providers import AIProvider


class OpencodeProvider(AIProvider):
    def __init__(self):
        self._path = shutil.which("opencode") or "opencode"

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
        return [self._path, "run", "-m", "anthropic/claude-haiku-4-5-20251001", prompt]

    def build_task_command(self, personality_prompt: str, working_dir: str, message: str) -> list[str]:
        combined = (
            f"IMPORTANT - You must stay in character as described below:\n"
            f"{personality_prompt}\n\n"
            f"Task: {message}"
        )
        return [
            self._path, "run",
            "-m", "anthropic/claude-sonnet-4-6",
            "--dir", working_dir,
            combined,
        ]
