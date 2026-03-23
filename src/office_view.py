from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)
from src.worker import Worker
from src.worker_widget import WorkerWidget


class RoomWidget(QFrame):
    """A single room in the office that contains worker cards."""

    def __init__(self, name: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.room_name = name
        self.setStyleSheet(f"""
            RoomWidget {{
                background: {color};
                border-radius: 8px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel(f"{icon} {name}")
        header.setStyleSheet(
            "font-size: 11px; text-transform: uppercase; "
            "letter-spacing: 1px; color: #aaa; font-weight: bold;"
        )
        self._layout.addWidget(header)

        self._workers_layout = QHBoxLayout()
        self._workers_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._layout.addLayout(self._workers_layout)
        self._layout.addStretch()

        self._empty_label = QLabel("(empty)")
        self._empty_label.setStyleSheet("color: #444; font-style: italic; font-size: 11px;")
        self._workers_layout.addWidget(self._empty_label)
        self._worker_widgets: dict[str, WorkerWidget] = {}

    def add_worker_widget(self, widget: WorkerWidget):
        self._empty_label.hide()
        self._workers_layout.addWidget(widget)
        self._worker_widgets[widget.worker.id] = widget

    def remove_worker_widget(self, worker_id: str):
        widget = self._worker_widgets.pop(worker_id, None)
        if widget:
            self._workers_layout.removeWidget(widget)
            widget.setParent(None)
        if not self._worker_widgets:
            self._empty_label.show()


class OfficeView(QWidget):
    worker_clicked = pyqtSignal(str)  # worker_id
    hire_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker_widgets: dict[str, WorkerWidget] = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Room grid
        grid = QGridLayout()
        grid.setSpacing(3)

        self.rooms = {
            "workspace": RoomWidget("Workspace", "💻", "#1a2332"),
            "kitchen": RoomWidget("Kitchen", "☕", "#2a1f1a"),
            "meeting_room": RoomWidget("Meeting Room", "🗣️", "#1a1a2e"),
            "hallway": RoomWidget("Hallway", "🚶", "#1a2222"),
        }

        grid.addWidget(self.rooms["workspace"], 0, 0)
        grid.addWidget(self.rooms["kitchen"], 0, 1)
        grid.addWidget(self.rooms["meeting_room"], 1, 0)
        grid.addWidget(self.rooms["hallway"], 1, 1)

        # Workspace takes more horizontal space
        grid.setColumnStretch(0, 2)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        main_layout.addLayout(grid)

        # Status bar
        status_bar = QHBoxLayout()
        self.status_counts = QLabel()
        self.status_counts.setStyleSheet("color: #888; font-size: 11px;")
        status_bar.addWidget(self.status_counts)
        status_bar.addStretch()

        self.total_salary_label = QLabel("$0/mo")
        self.total_salary_label.setStyleSheet("color: #888; font-size: 11px;")
        status_bar.addWidget(self.total_salary_label)

        hire_btn = QPushButton("+ Hire Worker")
        hire_btn.setStyleSheet("""
            QPushButton {
                background: #1a3a2a; color: #64ffda; border: 1px solid #64ffda;
                border-radius: 4px; padding: 6px 16px; font-size: 12px;
            }
            QPushButton:hover { background: #2a4a3a; }
        """)
        hire_btn.clicked.connect(self.hire_clicked.emit)
        status_bar.addWidget(hire_btn)

        main_layout.addLayout(status_bar)

    def add_worker(self, worker: Worker):
        widget = WorkerWidget(worker)
        widget.clicked.connect(self.worker_clicked.emit)
        self._worker_widgets[worker.id] = widget
        room = self.rooms.get(worker.current_room, self.rooms["workspace"])
        room.add_worker_widget(widget)

    def remove_worker(self, worker_id: str):
        widget = self._worker_widgets.pop(worker_id, None)
        if widget:
            for room in self.rooms.values():
                room.remove_worker_widget(worker_id)

    def update_worker(self, worker: Worker):
        widget = self._worker_widgets.get(worker.id)
        if not widget:
            return
        # Move to correct room if needed
        current_room_name = worker.current_room
        for room_key, room in self.rooms.items():
            if worker.id in room._worker_widgets and room_key != current_room_name:
                room.remove_worker_widget(worker.id)
                target_room = self.rooms.get(current_room_name, self.rooms["workspace"])
                target_room.add_worker_widget(widget)
                break
        widget.update_display()

    def update_status_bar(self, workers: list[Worker], total_salary: int):
        counts = {}
        for w in workers:
            counts[w.status] = counts.get(w.status, 0) + 1
        parts = []
        for status, count in sorted(counts.items()):
            parts.append(f"{count} {status}")
        self.status_counts.setText("  ".join(parts) if parts else "No workers")
        self.total_salary_label.setText(f"Total: ${total_salary:,}/mo")
