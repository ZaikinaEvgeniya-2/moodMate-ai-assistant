from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class Chef:
    """The office chef (boss) — always present, patrols rooms."""

    def __init__(self):
        self.current_room: str | None = None  # None means in his office (hidden)


class ChefWidget(QFrame):
    """Small visual card for the chef — non-clickable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFixedSize(140, 80)
        self.setStyleSheet("""
            ChefWidget {
                background: #2a2210;
                border-radius: 8px;
                border: 2px solid #ffd700;
                padding: 6px;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        emoji_label = QLabel("\U0001f468\u200d\U0001f373")  # 👨‍🍳
        emoji_label.setStyleSheet("font-size: 22px;")
        name_label = QLabel("Chef")
        name_label.setStyleSheet(
            "font-weight: bold; color: #ffd700; font-size: 13px;"
        )
        top_row.addWidget(emoji_label)
        top_row.addWidget(name_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.status_label = QLabel("Patrolling...")
        self.status_label.setStyleSheet("color: #cca800; font-size: 10px;")
        layout.addWidget(self.status_label)
