from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, pyqtSignal

from src.providers import get_provider


class AIEngine(QObject):
    """Manages AI CLI subprocesses for personality generation and task execution."""

    response_ready = pyqtSignal(str, str)  # (worker_id, response_text)
    generation_ready = pyqtSignal(str)  # (generated_json_text)
    error_occurred = pyqtSignal(str, str)  # (worker_id, error_message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._provider = get_provider()
        self._processes: dict[str, QProcess] = {}
        self._env = QProcessEnvironment.systemEnvironment()
        self._env.remove("CLAUDECODE")

    def generate_personality(self, role: str, salary: int, description: str = ""):
        cmd = self._provider.build_generate_command(role, salary, description)
        process = QProcess(self)
        process.setProcessEnvironment(self._env)
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
        cmd = self._provider.build_task_command(personality_prompt, working_dir, message)
        process = QProcess(self)
        process.setProcessEnvironment(self._env)
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
