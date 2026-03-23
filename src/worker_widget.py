from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout
from src.worker import Worker


STATUS_COLORS = {
    "idle": "#888888",
    "received_task": "#2196f3",
    "working": "#4caf50",
    "done": "#4caf50",
    "partially_done": "#ff9800",
    "on_break": "#ff9800",
    "in_kitchen": "#ff9800",
    "wandering": "#f44336",
    "making_excuses": "#f44336",
    "chatting": "#e91e63",
}

STATUS_LABELS = {
    "idle": "Waiting for task",
    "received_task": "Received task",
    "working": "Working",
    "done": "Done",
    "partially_done": "Partially done",
    "on_break": "On break",
    "in_kitchen": "Drinking tea",
    "wandering": "Wandering around",
    "making_excuses": "Making excuses",
    "chatting": "Chatting",
}


class WorkerWidget(QFrame):
    clicked = pyqtSignal(str)  # emits worker_id

    def __init__(self, worker: Worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedSize(180, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            WorkerWidget {
                background: #1a2332;
                border-radius: 8px;
                border-left: 3px solid #888;
                padding: 8px;
            }
            WorkerWidget:hover {
                background: #223344;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Emoji + Name row
        top_row = QHBoxLayout()
        self.emoji_label = QLabel(self.worker.emoji)
        self.emoji_label.setStyleSheet("font-size: 24px;")
        self.name_label = QLabel(self.worker.name)
        self.name_label.setStyleSheet("font-weight: bold; color: white; font-size: 14px;")
        top_row.addWidget(self.emoji_label)
        top_row.addWidget(self.name_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Status row
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.status_label)

        # Salary row
        self.salary_label = QLabel(f"${self.worker.salary:,}/mo")
        self.salary_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.salary_label)

        # Task row
        self.task_label = QLabel("")
        self.task_label.setStyleSheet("color: #888; font-size: 9px;")
        self.task_label.setWordWrap(True)
        layout.addWidget(self.task_label)

        self.update_display()

    def update_display(self):
        color = STATUS_COLORS.get(self.worker.status, "#888")
        label = STATUS_LABELS.get(self.worker.status, self.worker.status)
        self.status_label.setText(f"● {label}")
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.setStyleSheet(f"""
            WorkerWidget {{
                background: #1a2332;
                border-radius: 8px;
                border-left: 3px solid {color};
                padding: 8px;
            }}
            WorkerWidget:hover {{
                background: #223344;
            }}
        """)

    def set_task_text(self, text: str):
        if len(text) > 30:
            text = text[:27] + "..."
        self.task_label.setText(f"Task: {text}" if text else "")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.worker.id)
        super().mousePressEvent(event)
