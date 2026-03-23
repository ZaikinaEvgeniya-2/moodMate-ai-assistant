import logging
import time

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, pyqtSignal

from src.providers import get_provider

PROCESS_TIMEOUT_MS = 90_000  # 90 seconds

logger = logging.getLogger("ai_engine")


class AIEngine(QObject):
    """Manages AI CLI subprocesses for personality generation and task execution."""

    response_ready = pyqtSignal(str, str)  # (worker_id, response_text)
    generation_ready = pyqtSignal(str)  # (generated_json_text)
    error_occurred = pyqtSignal(str, str)  # (worker_id, error_message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._provider = get_provider()
        self._processes: dict[str, QProcess] = {}
        self._gen_process: QProcess | None = None  # prevent GC during generation
        self._env = QProcessEnvironment.systemEnvironment()
        self._env.remove("CLAUDECODE")
        logger.info(f"AIEngine initialized with provider: {type(self._provider).__name__}")

    def generate_personality(self, role: str, salary: int, description: str = ""):
        cmd = self._provider.build_generate_command(role, salary, description)
        logger.info(f"[generate] Starting: {cmd[0]} {' '.join(cmd[1:3])}")
        logger.debug(f"[generate] Full command: {cmd}")

        process = QProcess(self)
        process.setProcessEnvironment(self._env)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._gen_process = process  # prevent GC while running

        start_time = time.monotonic()

        def on_started():
            pid = process.processId()
            logger.info(f"[generate] Process started, PID={pid}")

        def on_error_occurred(error):
            logger.error(f"[generate] QProcess error: {error} ({_qprocess_error_string(error)})")

        def on_finished(exit_code, exit_status):
            elapsed = time.monotonic() - start_time
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            logger.info(f"[generate] Process finished: exit_code={exit_code}, "
                        f"exit_status={exit_status}, elapsed={elapsed:.1f}s, "
                        f"output_length={len(output)}")
            if output:
                preview = output[:500] + ("..." if len(output) > 500 else "")
                logger.debug(f"[generate] Output preview: {preview}")

            if exit_code == 0:
                self.generation_ready.emit(output)
            else:
                error_msg = f"Generation failed (exit {exit_code}): {output}"
                logger.error(f"[generate] {error_msg}")
                self.error_occurred.emit("", error_msg)
            self._gen_process = None
            process.deleteLater()

        process.started.connect(on_started)
        process.errorOccurred.connect(on_error_occurred)
        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])
        process.closeWriteChannel()  # signal no stdin, so CLI won't hang

        if not process.waitForStarted(5000):
            logger.error(f"[generate] Failed to start process within 5s. "
                         f"State: {process.state()}, Error: {process.error()}")

        # Timeout guard
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._kill_if_running(process, "generate"))
        timer.start(PROCESS_TIMEOUT_MS)
        process.finished.connect(timer.stop)

    def run_task(self, worker_id: str, personality_prompt: str,
                 working_dir: str, message: str):
        cmd = self._provider.build_task_command(personality_prompt, working_dir, message)
        logger.info(f"[task:{worker_id}] Starting: {cmd[0]} {' '.join(cmd[1:5])}")
        logger.debug(f"[task:{worker_id}] Full command: {cmd}")
        logger.debug(f"[task:{worker_id}] Working dir: {working_dir}")

        process = QProcess(self)
        process.setProcessEnvironment(self._env)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        if working_dir:
            process.setWorkingDirectory(working_dir)
        self._processes[worker_id] = process

        start_time = time.monotonic()

        def on_started():
            pid = process.processId()
            logger.info(f"[task:{worker_id}] Process started, PID={pid}")

        def on_error_occurred(error):
            logger.error(f"[task:{worker_id}] QProcess error: {error} "
                         f"({_qprocess_error_string(error)})")

        def on_finished(exit_code, exit_status):
            elapsed = time.monotonic() - start_time
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            logger.info(f"[task:{worker_id}] Process finished: exit_code={exit_code}, "
                        f"exit_status={exit_status}, elapsed={elapsed:.1f}s, "
                        f"output_length={len(output)}")
            if output:
                preview = output[:500] + ("..." if len(output) > 500 else "")
                logger.debug(f"[task:{worker_id}] Output preview: {preview}")

            if exit_code == 0:
                self.response_ready.emit(worker_id, output)
            else:
                error_msg = f"Task failed (exit {exit_code}): {output}"
                logger.error(f"[task:{worker_id}] {error_msg}")
                self.error_occurred.emit(worker_id, error_msg)
            self._processes.pop(worker_id, None)
            process.deleteLater()

        process.started.connect(on_started)
        process.errorOccurred.connect(on_error_occurred)
        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])
        process.closeWriteChannel()  # signal no stdin, so CLI won't hang

        if not process.waitForStarted(5000):
            logger.error(f"[task:{worker_id}] Failed to start process within 5s. "
                         f"State: {process.state()}, Error: {process.error()}")

        # Timeout guard
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._kill_if_running(process, f"task:{worker_id}"))
        timer.start(PROCESS_TIMEOUT_MS)
        process.finished.connect(timer.stop)

    def _kill_if_running(self, process: QProcess, label: str):
        if process.state() != QProcess.ProcessState.NotRunning:
            logger.error(f"[{label}] Timed out after {PROCESS_TIMEOUT_MS // 1000}s, killing process")
            process.kill()

    def is_worker_busy(self, worker_id: str) -> bool:
        return worker_id in self._processes


def _qprocess_error_string(error: QProcess.ProcessError) -> str:
    """Convert QProcess.ProcessError enum to human-readable string."""
    mapping = {
        QProcess.ProcessError.FailedToStart: "FailedToStart (binary not found or no permissions)",
        QProcess.ProcessError.Crashed: "Crashed",
        QProcess.ProcessError.Timedout: "Timedout",
        QProcess.ProcessError.WriteError: "WriteError",
        QProcess.ProcessError.ReadError: "ReadError",
        QProcess.ProcessError.UnknownError: "UnknownError",
    }
    return mapping.get(error, f"Unknown({error})")
