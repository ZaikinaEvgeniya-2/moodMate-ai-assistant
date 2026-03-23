import shutil
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class AIEngine(QObject):
    """Manages Claude CLI subprocesses for personality generation and task execution."""

    response_ready = pyqtSignal(str, str)  # (worker_id, response_text)
    generation_ready = pyqtSignal(str)  # (generated_json_text)
    error_occurred = pyqtSignal(str, str)  # (worker_id, error_message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._claude_path = shutil.which("claude") or "claude"
        self._processes: dict[str, QProcess] = {}

    def _build_generate_command(self, role: str, salary: int, description: str) -> list[str]:
        prompt = (
            f"Generate a worker personality for a {role} with salary ${salary}. "
            f"Additional info: {description}. "
            "Include: name, emoji (single emoji for avatar), 3 personality traits, "
            "work style, favorite excuse for not working, catchphrase. "
            "Return ONLY valid JSON with keys: name, emoji, traits (array of 3 strings), "
            "catchphrase, favorite_excuse, personality_prompt (a 2-3 sentence system prompt "
            "describing this character's personality and work ethic for future interactions)."
        )
        return [self._claude_path, "--print", prompt]

    def _build_task_command(self, personality_prompt: str, working_dir: str,
                            message: str) -> list[str]:
        return [
            self._claude_path, "--print",
            "--system-prompt", personality_prompt,
            "--allowedTools", "Read,Write,Edit,Glob,Grep",
            "--working-dir", working_dir,
            message,
        ]

    def generate_personality(self, role: str, salary: int, description: str = ""):
        cmd = self._build_generate_command(role, salary, description)
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def on_finished(exit_code, exit_status):
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if exit_code == 0:
                self.generation_ready.emit(output)
            else:
                self.error_occurred.emit("", f"Generation failed: {output}")
            process.deleteLater()

        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])

    def run_task(self, worker_id: str, personality_prompt: str,
                 working_dir: str, message: str):
        cmd = self._build_task_command(personality_prompt, working_dir, message)
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._processes[worker_id] = process

        def on_finished(exit_code, exit_status):
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if exit_code == 0:
                self.response_ready.emit(worker_id, output)
            else:
                self.error_occurred.emit(worker_id, f"Task failed: {output}")
            self._processes.pop(worker_id, None)
            process.deleteLater()

        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])

    def is_worker_busy(self, worker_id: str) -> bool:
        return worker_id in self._processes
