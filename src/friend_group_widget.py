from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout
from src.worker import Worker


class FriendGroupWidget(QFrame):
    """Grouped card shown when two friends are chatting in the same room."""
    clicked = pyqtSignal(str, str)  # (worker_id_a, worker_id_b)

    def __init__(self, worker_a: Worker, worker_b: Worker, level: int, parent=None):
        super().__init__(parent)
        self.worker_a = worker_a
        self.worker_b = worker_b
        self.level = level
        self._conversation_lines: list[dict] = []

        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedHeight(120)
        self.setMinimumWidth(300)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        self._setup_ui()

    def _update_style(self):
        self.setStyleSheet("""
            FriendGroupWidget {
                background: #1e2a3a;
                border-radius: 12px;
                border: 2px solid #e91e63;
                padding: 8px;
            }
            FriendGroupWidget:hover {
                background: #2a3a4a;
            }
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()

        a_label = QLabel(f"{self.worker_a.emoji} {self.worker_a.name}")
        a_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")
        top_row.addWidget(a_label)

        heart = QLabel("❤️")
        heart.setStyleSheet("font-size: 16px;")
        top_row.addWidget(heart)

        b_label = QLabel(f"{self.worker_b.emoji} {self.worker_b.name}")
        b_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")
        top_row.addWidget(b_label)

        top_row.addStretch()

        level_badge = QLabel(f"Lv.{self.level}")
        level_badge.setStyleSheet(
            "background: #e91e63; color: white; padding: 2px 8px; "
            "border-radius: 4px; font-size: 10px; font-weight: bold;"
        )
        top_row.addWidget(level_badge)

        layout.addLayout(top_row)

        status = QLabel("● Chatting")
        status.setStyleSheet("color: #e91e63; font-size: 11px;")
        layout.addWidget(status)

        self.snippet_label = QLabel("")
        self.snippet_label.setStyleSheet(
            "color: #aaa; font-size: 11px; font-style: italic;"
        )
        self.snippet_label.setWordWrap(True)
        layout.addWidget(self.snippet_label)

        read_link = QLabel("📖 Read conversation")
        read_link.setStyleSheet("color: #64ffda; font-size: 10px;")
        layout.addWidget(read_link)

    def update_conversation(self, lines: list[dict]):
        """Update the conversation snippet with latest lines."""
        self._conversation_lines = lines
        if lines:
            last = lines[-1]
            text = last.get("text", "")
            if len(text) > 50:
                text = text[:47] + "..."
            self.snippet_label.setText(f'"{text}"')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.worker_a.id, self.worker_b.id)
        super().mousePressEvent(event)
