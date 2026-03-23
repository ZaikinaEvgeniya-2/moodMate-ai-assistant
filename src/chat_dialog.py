# src/chat_dialog.py
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)
from src.worker import Worker
from src.worker_widget import STATUS_COLORS, STATUS_LABELS


class ChatDialog(QDialog):
    message_sent = pyqtSignal(str, str)  # (worker_id, message)
    fire_requested = pyqtSignal(str)  # worker_id
    working_dir_changed = pyqtSignal(str, str)  # (worker_id, new_path)
    chat_cleared = pyqtSignal(str)  # worker_id

    def __init__(self, worker: Worker, messages: list[dict], parent=None):
        super().__init__(parent)
        self.worker = worker
        self.setWindowTitle(f"Chat with {worker.name}")
        self.setMinimumSize(500, 500)
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: white; }
            QLabel { color: white; }
        """)
        self._setup_ui(messages)
        self.input_field.setFocus()

    def _setup_ui(self, messages: list[dict]):
        layout = QVBoxLayout(self)

        # Header
        header = QHBoxLayout()
        emoji = QLabel(self.worker.emoji)
        emoji.setStyleSheet("font-size: 32px;")
        header.addWidget(emoji)

        info = QVBoxLayout()
        name_label = QLabel(f"{self.worker.name} — {self.worker.role.title()}")
        name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        info.addWidget(name_label)

        salary_tier = QLabel(f"${self.worker.salary:,}/mo  •  {self.worker.tier.value.title()}")
        salary_tier.setStyleSheet("color: #888; font-size: 12px;")
        info.addWidget(salary_tier)

        header.addLayout(info)
        header.addStretch()

        status_color = STATUS_COLORS.get(self.worker.status, "#888")
        status_text = STATUS_LABELS.get(self.worker.status, self.worker.status)
        status_label = QLabel(f"● {status_text}")
        status_label.setStyleSheet(f"color: {status_color}; font-size: 12px;")
        header.addWidget(status_label)
        layout.addLayout(header)

        # Traits
        if self.worker.traits:
            traits_layout = QHBoxLayout()
            for trait in self.worker.traits:
                badge = QLabel(trait)
                badge.setStyleSheet(
                    "background: #1a2332; color: #64ffda; padding: 2px 8px; "
                    "border-radius: 4px; font-size: 10px;"
                )
                traits_layout.addWidget(badge)
            traits_layout.addStretch()
            layout.addLayout(traits_layout)

        # Working directory
        dir_row = QHBoxLayout()
        dir_label = QLabel("📁")
        dir_label.setStyleSheet("font-size: 14px;")
        dir_row.addWidget(dir_label)
        self.dir_display = QLabel(self.worker.working_dir or "(default sandbox)")
        self.dir_display.setStyleSheet("color: #888; font-size: 11px;")
        self.dir_display.setToolTip(self.worker.working_dir or "data/workers/<id>/")
        dir_row.addWidget(self.dir_display)
        dir_row.addStretch()
        change_dir_btn = QPushButton("Change")
        change_dir_btn.setStyleSheet(
            "background: #161b22; color: #888; border: 1px solid #333; "
            "border-radius: 4px; padding: 3px 10px; font-size: 10px;"
        )
        change_dir_btn.setAutoDefault(False)
        change_dir_btn.setDefault(False)
        change_dir_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        change_dir_btn.clicked.connect(self._change_working_dir)
        dir_row.addWidget(change_dir_btn)
        layout.addLayout(dir_row)

        # Chat area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #333; border-radius: 4px; }")
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.chat_widget)
        layout.addWidget(self.scroll)

        for msg in messages:
            self._add_message(msg["role"], msg["content"])

        # Input area
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type a message...")
        self.input_field.setStyleSheet(
            "background: #161b22; color: white; border: 1px solid #333; "
            "border-radius: 4px; padding: 8px; font-size: 13px;"
        )
        self.input_field.returnPressed.connect(self._send_message)
        input_row.addWidget(self.input_field)

        send_btn = QPushButton("→")
        send_btn.setStyleSheet(
            "background: #238636; color: white; border-radius: 4px; "
            "padding: 8px 14px; font-size: 14px;"
        )
        send_btn.setAutoDefault(False)
        send_btn.setDefault(False)
        send_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        send_btn.clicked.connect(self._send_message)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        # Fire button
        fire_btn = QPushButton("Fire 🔥")
        fire_btn.setStyleSheet(
            "background: #3a1515; color: #f44336; border: 1px solid #f44336; "
            "border-radius: 4px; padding: 6px 16px; font-size: 11px;"
        )
        fire_btn.setAutoDefault(False)
        fire_btn.setDefault(False)
        fire_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        fire_btn.clicked.connect(lambda: self.fire_requested.emit(self.worker.id))

        bottom_row = QHBoxLayout()
        clear_btn = QPushButton("Clear Chat")
        clear_btn.setStyleSheet(
            "background: #161b22; color: #888; border: 1px solid #333; "
            "border-radius: 4px; padding: 6px 16px; font-size: 11px;"
        )
        clear_btn.setAutoDefault(False)
        clear_btn.setDefault(False)
        clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        clear_btn.clicked.connect(self._clear_chat)
        bottom_row.addWidget(clear_btn)
        bottom_row.addStretch()
        bottom_row.addWidget(fire_btn)
        layout.addLayout(bottom_row)

    def keyPressEvent(self, event):
        # Prevent QDialog from closing or activating buttons on Enter/Return —
        # we handle Enter via QLineEdit.returnPressed instead.
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return
        super().keyPressEvent(event)

    def _add_message(self, role: str, content: str):
        if role == "user":
            label = QLabel(f"You: {content}")
            label.setStyleSheet("color: #64ffda; font-size: 12px; padding: 4px;")
        else:
            label = QLabel(f"{self.worker.name}: {content}")
            label.setStyleSheet("color: #ccc; font-size: 12px; padding: 4px;")
        label.setWordWrap(True)
        self.chat_layout.addWidget(label)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        vbar = self.scroll.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def add_response(self, content: str):
        self._add_message("worker", content)

    def _clear_chat(self):
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.chat_cleared.emit(self.worker.id)

    def _change_working_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Working Directory")
        if path:
            self.worker.working_dir = path
            self.dir_display.setText(path)
            self.dir_display.setToolTip(path)
            self.working_dir_changed.emit(self.worker.id, path)

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._add_message("user", text)
        self.message_sent.emit(self.worker.id, text)
