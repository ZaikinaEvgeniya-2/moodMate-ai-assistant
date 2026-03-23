import logging
import os
import shutil

from src.providers import AIProvider

logger = logging.getLogger("opencode_provider")

DEFAULT_MODEL = "opencode/nemotron-3-super-free"


class OpencodeProvider(AIProvider):
    def __init__(self):
        self._path = shutil.which("opencode") or "opencode"
        self._model_generate = os.environ.get("AI_MODEL_GENERATE", DEFAULT_MODEL)
        self._model_task = os.environ.get("AI_MODEL_TASK", DEFAULT_MODEL)
        logger.info(f"OpencodeProvider initialized, binary: {self._path}, "
                    f"generate_model: {self._model_generate}, task_model: {self._model_task}")

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
        cmd = [self._path, "run", "-m", self._model_generate, prompt]
        logger.debug(f"[generate] command: {cmd[:4]} + [prompt ({len(prompt)} chars)]")
        return cmd

    def build_task_command(self, personality_prompt: str, working_dir: str, message: str) -> list[str]:
        combined = (
            f"IMPORTANT - You must stay in character as described below:\n"
            f"{personality_prompt}\n\n"
            f"Task: {message}"
        )
        cmd = [
            self._path, "run",
            "-m", self._model_task,
            "--dir", working_dir,
            combined,
        ]
        logger.debug(f"[task] command: {cmd[:6]} + [prompt ({len(combined)} chars)]")
        return cmd
