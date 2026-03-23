from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QTabWidget, QVBoxLayout, QWidget,
)
from src.worker import Worker


class FriendChatDialog(QDialog):
    """Read-only dialog showing conversations between two friend workers."""

    def __init__(self, worker_a: Worker, worker_b: Worker, level: int,
                 current_lines: list[dict], history: list[dict], parent=None):
        super().__init__(parent)
        self.worker_a = worker_a
        self.worker_b = worker_b
        self.setWindowTitle(f"{worker_a.name} ❤️ {worker_b.name} — Friends (Lv.{level})")
        self.setMinimumSize(450, 400)
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: white; }
            QLabel { color: white; }
            QTabWidget::pane { border: 1px solid #333; background: #0d1117; }
            QTabBar::tab {
                background: #161b22; color: #888; padding: 6px 16px;
                border: 1px solid #333; border-bottom: none;
            }
            QTabBar::tab:selected { background: #0d1117; color: white; }
        """)
        self._setup_ui(current_lines, history, level)

    def _setup_ui(self, current_lines, history, level):
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        emoji_a = QLabel(self.worker_a.emoji)
        emoji_a.setStyleSheet("font-size: 28px;")
        header.addWidget(emoji_a)

        heart = QLabel("❤️")
        heart.setStyleSheet("font-size: 20px;")
        header.addWidget(heart)

        emoji_b = QLabel(self.worker_b.emoji)
        emoji_b.setStyleSheet("font-size: 28px;")
        header.addWidget(emoji_b)

        names = QLabel(f"{self.worker_a.name} & {self.worker_b.name}")
        names.setStyleSheet("font-size: 16px; font-weight: bold; margin-left: 8px;")
        header.addWidget(names)
        header.addStretch()

        level_badge = QLabel(f"Lv.{level}")
        level_badge.setStyleSheet(
            "background: #e91e63; color: white; padding: 3px 10px; "
            "border-radius: 4px; font-size: 11px; font-weight: bold;"
        )
        header.addWidget(level_badge)
        layout.addLayout(header)

        tabs = QTabWidget()

        current_tab = self._build_conversation_widget(current_lines)
        tabs.addTab(current_tab, "Current")

        history_tab = self._build_history_widget(history)
        tabs.addTab(history_tab, f"History ({len(history)})")

        layout.addWidget(tabs)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(
            "background: #161b22; color: #888; border: 1px solid #333; "
            "border-radius: 4px; padding: 6px 20px; font-size: 12px;"
        )
        close_btn.clicked.connect(self.close)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _build_conversation_widget(self, lines: list[dict]) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if not lines:
            empty = QLabel("Generating conversation...")
            empty.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            content_layout.addWidget(empty)
        else:
            for line in lines:
                worker_id = line.get("worker_id", "")
                text = line.get("text", "")
                if worker_id == self.worker_a.id:
                    prefix = f"{self.worker_a.emoji} {self.worker_a.name}"
                    color = "#64ffda"
                else:
                    prefix = f"{self.worker_b.emoji} {self.worker_b.name}"
                    color = "#ff9800"
                label = QLabel(f"{prefix}: {text}")
                label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 4px;")
                label.setWordWrap(True)
                content_layout.addWidget(label)

        scroll.setWidget(content)
        return scroll

    def _build_history_widget(self, history: list[dict]) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        if not history:
            empty = QLabel("No previous conversations")
            empty.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            content_layout.addWidget(empty)
        else:
            for conv in reversed(history):
                timestamp = conv.get("timestamp", "")
                ts_label = QLabel(f"--- {timestamp} ---")
                ts_label.setStyleSheet(
                    "color: #555; font-size: 10px; padding: 8px 4px 2px 4px;"
                )
                content_layout.addWidget(ts_label)

                for line in conv.get("lines", []):
                    worker_id = line.get("worker_id", "")
                    text = line.get("text", "")
                    if worker_id == self.worker_a.id:
                        prefix = f"{self.worker_a.emoji} {self.worker_a.name}"
                        color = "#64ffda"
                    else:
                        prefix = f"{self.worker_b.emoji} {self.worker_b.name}"
                        color = "#ff9800"
                    label = QLabel(f"{prefix}: {text}")
                    label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 2px 4px;")
                    label.setWordWrap(True)
                    content_layout.addWidget(label)

        scroll.setWidget(content)
        return scroll
