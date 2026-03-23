# src/main.py
import logging
import sys
from pathlib import Path

# Ensure project root is on Python path so `from src.` imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Configure logging — DEBUG level shows full command/output details
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)

import random

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from src.ai_engine import AIEngine
from src.chat_dialog import ChatDialog
from src.chef import Chef
from src.hire_dialog import HireDialog
from src.office_view import OfficeView
from src.personality import BehaviorEngine
from src.worker_manager import WorkerManager


DATA_DIR = Path(__file__).parent.parent / "data"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Office Simulator")
        self.setMinimumSize(900, 650)
        self.setStyleSheet("background: #0d1117; color: white;")

        self.ai_engine = AIEngine(self)
        self.behavior = BehaviorEngine()
        self.manager = WorkerManager(data_dir=DATA_DIR)
        self.manager.load()

        self._active_chat: ChatDialog | None = None
        self._pending_timers: dict[str, QTimer] = {}
        self._pending_messages: dict[str, str] = {}

        # Office view
        self.office = OfficeView()
        self.setCentralWidget(self.office)
        self.office.hire_clicked.connect(self._open_hire_dialog)
        self.office.worker_clicked.connect(self._open_chat)

        # AI engine signals
        self.ai_engine.response_ready.connect(self._on_task_response)
        self.ai_engine.error_occurred.connect(self._on_task_error)

        # Load existing workers into view
        for worker in self.manager.workers:
            self.office.add_worker(worker)
        self._refresh_status_bar()

        # Chef patrol
        self.chef = Chef()
        self.office.add_chef()
        self._chef_timer = QTimer(self)
        self._chef_timer.timeout.connect(self._chef_patrol)
        self._start_chef_timer()

    def _refresh_status_bar(self):
        self.office.update_status_bar(self.manager.workers, self.manager.total_salary)

    def _open_hire_dialog(self):
        dlg = HireDialog(self.ai_engine, self)
        if dlg.exec() and dlg.generated_worker:
            worker = dlg.generated_worker
            self.manager.add_worker(worker)
            self.office.add_worker(worker)
            self._refresh_status_bar()

    def _open_chat(self, worker_id: str):
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return
        messages = self.manager.load_chat(worker_id)
        dlg = ChatDialog(worker, messages, self)
        dlg.message_sent.connect(self._on_chat_message)
        dlg.fire_requested.connect(self._fire_worker)
        dlg.working_dir_changed.connect(self._on_working_dir_changed)
        dlg.chat_cleared.connect(lambda wid: self.manager.save_chat(wid, []))
        self._active_chat = dlg
        dlg.exec()
        self._active_chat = None

    def _on_chat_message(self, worker_id: str, message: str):
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return

        # Save user message
        messages = self.manager.load_chat(worker_id)
        messages.append({"role": "user", "content": message})
        self.manager.save_chat(worker_id, messages)

        # Behavior: decide what worker does
        worker.status = "received_task"
        self.office.update_worker(worker)
        self._refresh_status_bar()

        new_status, delay = self.behavior.decide_next_status(worker)

        if delay > 0:
            # Worker procrastinates first — track the pending message
            self._pending_messages[worker_id] = message
            worker.status = new_status
            self.office.update_worker(worker)
            self.manager.save()
            self._refresh_status_bar()

            # After delay, maybe work or procrastinate more
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._after_delay(worker_id, message))
            timer.start(delay * 1000)
            self._pending_timers[worker_id] = timer
        else:
            worker.status = new_status
            self.office.update_worker(worker)
            self._refresh_status_bar()
            if new_status == "working":
                self._pending_messages.pop(worker_id, None)
                self._run_task(worker_id, message)

    def _after_delay(self, worker_id: str, original_message: str):
        self._pending_timers.pop(worker_id, None)
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return

        new_status, delay = self.behavior.decide_next_status(worker)
        worker.status = new_status
        self.office.update_worker(worker)
        self.manager.save()
        self._refresh_status_bar()

        if new_status == "working":
            self._pending_messages.pop(worker_id, None)
            self._run_task(worker_id, original_message)
        elif delay > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._after_delay(worker_id, original_message))
            timer.start(delay * 1000)
            self._pending_timers[worker_id] = timer
        else:
            # Worker gave up, add a snarky message
            self._pending_messages.pop(worker_id, None)
            messages = self.manager.load_chat(worker_id)
            messages.append({
                "role": "worker",
                "content": worker.favorite_excuse or "I'll do it later... maybe.",
            })
            self.manager.save_chat(worker_id, messages)
            if self._active_chat and self._active_chat.worker.id == worker_id:
                self._active_chat.add_response(
                    worker.favorite_excuse or "I'll do it later... maybe."
                )

    def _run_task(self, worker_id: str, message: str):
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return
        working_dir = worker.working_dir or str(DATA_DIR / "workers" / worker.id)
        self.ai_engine.run_task(worker_id, worker.personality_prompt, working_dir, message)

    def _on_task_response(self, worker_id: str, response: str):
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return

        # Decide if worker actually finishes or is lazy about it
        if self.behavior.should_take_break(worker):
            worker.status = "partially_done"
        else:
            worker.status = "done"

        self.office.update_worker(worker)
        self.manager.save()
        self._refresh_status_bar()

        # Save response to chat
        messages = self.manager.load_chat(worker_id)
        messages.append({"role": "worker", "content": response})
        self.manager.save_chat(worker_id, messages)

        # Update active chat if open
        if self._active_chat and self._active_chat.worker.id == worker_id:
            self._active_chat.add_response(response)

        # Reset to idle after a moment
        QTimer.singleShot(3000, lambda: self._reset_worker(worker_id))

    def _on_task_error(self, worker_id: str, error: str):
        worker = self.manager.get_worker(worker_id)
        if worker:
            worker.status = "idle"
            self.office.update_worker(worker)
            self._refresh_status_bar()

        messages = self.manager.load_chat(worker_id)
        messages.append({"role": "worker", "content": f"(Error: {error})"})
        self.manager.save_chat(worker_id, messages)

        if self._active_chat and self._active_chat.worker.id == worker_id:
            self._active_chat.add_response(f"(Error: {error})")

    def _reset_worker(self, worker_id: str):
        worker = self.manager.get_worker(worker_id)
        if worker and worker.status in ("done", "partially_done"):
            worker.status = "idle"
            self.office.update_worker(worker)
            self.manager.save()
            self._refresh_status_bar()

    def _on_working_dir_changed(self, worker_id: str, path: str):
        worker = self.manager.get_worker(worker_id)
        if worker:
            worker.working_dir = path
            self.manager.save()

    # --- Chef patrol ---

    def _start_chef_timer(self):
        interval = random.randint(8, 15) * 1000
        self._chef_timer.start(interval)

    def _chef_patrol(self):
        self._chef_timer.stop()

        # Build the patrol route — workspace & kitchen appear more often
        if not hasattr(self, "_patrol_route") or not self._patrol_route:
            rooms = [
                "workspace", "workspace", "workspace",
                "kitchen", "kitchen",
                "hallway",
                "meeting_room",
            ]
            random.shuffle(rooms)
            # Deduplicate consecutive duplicates so chef doesn't "stay" in same room
            route: list[str] = [rooms[0]]
            for r in rooms[1:]:
                if r != route[-1]:
                    route.append(r)
            self._patrol_route = route

        # Visit the next room in the route
        room = self._patrol_route.pop(0)
        self.chef.current_room = room
        self.office.move_chef(room)
        self._chef_catch_slackers(room)

        if self._patrol_route:
            # More rooms to visit — move to the next one after a short delay
            QTimer.singleShot(random.randint(3, 5) * 1000, self._chef_patrol)
        else:
            # Patrol done — chef goes back to his office after a brief stay
            QTimer.singleShot(random.randint(3, 5) * 1000, self._chef_return_to_office)

    def _chef_return_to_office(self):
        self.chef.current_room = None
        self.office.hide_chef()
        self._start_chef_timer()

    _SLACKING_STATUSES = {"on_break", "in_kitchen", "wandering", "making_excuses"}

    def _chef_catch_slackers(self, room: str):
        for worker in self.manager.workers:
            if worker.current_room != room:
                continue
            is_slacking = worker.status in self._SLACKING_STATUSES
            is_idle_with_task = (
                worker.status == "idle" and worker.id in self._pending_messages
            )
            if not (is_slacking or is_idle_with_task):
                continue

            # Cancel any procrastination timer
            timer = self._pending_timers.pop(worker.id, None)
            if timer:
                timer.stop()

            # Show sorry emoji in current room for 5 seconds (don't move yet)
            sorry_widget = self.office._worker_widgets.get(worker.id)
            if sorry_widget:
                sorry_widget.status_label.setText("\U0001f630 Sorry!")  # 😰
                sorry_widget.status_label.setStyleSheet(
                    "color: #ff6b6b; font-size: 11px;"
                )

            # After 5 seconds, move worker to workspace and start task
            pending_msg = self._pending_messages.pop(worker.id, None)
            QTimer.singleShot(
                5000,
                lambda wid=worker.id, msg=pending_msg: self._chef_send_to_work(wid, msg),
            )

    def _chef_send_to_work(self, worker_id: str, pending_msg: str | None):
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return
        if pending_msg:
            worker.status = "working"
            self.office.update_worker(worker)
            self._refresh_status_bar()
            self._run_task(worker_id, pending_msg)
        else:
            worker.status = "idle"
            self.office.update_worker(worker)
            self._refresh_status_bar()

    def _fire_worker(self, worker_id: str):
        worker = self.manager.get_worker(worker_id)
        if not worker:
            return
        reply = QMessageBox.question(
            self, "Fire Worker",
            f"Are you sure you want to fire {worker.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._active_chat:
                self._active_chat.close()
                self._active_chat = None
            self.office.remove_worker(worker_id)
            self.manager.remove_worker(worker_id)
            self._refresh_status_bar()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
