import json
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSlider, QTextEdit, QVBoxLayout,
)
from src.worker import Worker, SalaryTier
from src.ai_engine import AIEngine


TIER_LABELS = {
    (0, 199): ("😴 Lazy", "#f44336"),
    (200, 499): ("😐 Mediocre", "#ff9800"),
    (500, 999): ("💼 Decent", "#2196f3"),
    (1000, 2000): ("⭐ Star", "#4caf50"),
}

ROLES = ["Developer", "Writer", "Designer", "Tester", "DevOps", "Other"]


class HireDialog(QDialog):
    def __init__(self, ai_engine: AIEngine, parent=None):
        super().__init__(parent)
        self.ai_engine = ai_engine
        self.generated_worker: Worker | None = None
        self.setWindowTitle("Hire New Worker")
        self.setMinimumSize(450, 500)
        self.setStyleSheet("""
            QDialog { background: #0d1117; color: white; }
            QLabel { color: white; }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("🏢 Hire New Worker")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Role
        layout.addWidget(QLabel("Role:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(ROLES)
        self.role_combo.setStyleSheet(
            "background: #161b22; color: white; padding: 6px; border: 1px solid #333;"
        )
        layout.addWidget(self.role_combo)

        # Salary slider
        salary_row = QHBoxLayout()
        salary_row.addWidget(QLabel("Salary:"))
        self.salary_slider = QSlider(Qt.Orientation.Horizontal)
        self.salary_slider.setRange(0, 2000)
        self.salary_slider.setValue(500)
        self.salary_slider.setTickInterval(100)
        self.salary_slider.valueChanged.connect(self._update_salary_label)
        salary_row.addWidget(self.salary_slider)
        self.salary_label = QLabel("$500/mo")
        self.salary_label.setStyleSheet("font-weight: bold; min-width: 80px;")
        salary_row.addWidget(self.salary_label)
        layout.addLayout(salary_row)

        self.tier_label = QLabel()
        self.tier_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.tier_label)
        self._update_salary_label(500)

        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Good at Python, loves cats...")
        self.description_input.setStyleSheet(
            "background: #161b22; color: white; padding: 6px; border: 1px solid #333;"
        )
        layout.addWidget(self.description_input)

        # Generate button
        self.generate_btn = QPushButton("Generate Personality")
        self.generate_btn.setStyleSheet(
            "background: #1a3a2a; color: #64ffda; border: 1px solid #64ffda; "
            "border-radius: 4px; padding: 8px; font-size: 13px;"
        )
        self.generate_btn.clicked.connect(self._generate)
        layout.addWidget(self.generate_btn)

        # Preview area
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet(
            "background: #161b22; border: 1px solid #333; border-radius: 4px; "
            "padding: 12px; font-size: 12px;"
        )
        self.preview_label.setWordWrap(True)
        self.preview_label.setMinimumHeight(100)
        layout.addWidget(self.preview_label)

        # Action buttons
        btn_row = QHBoxLayout()
        self.retry_btn = QPushButton("Try Again")
        self.retry_btn.setStyleSheet(
            "background: #161b22; color: #888; border: 1px solid #333; "
            "border-radius: 4px; padding: 8px;"
        )
        self.retry_btn.clicked.connect(self._generate)
        self.retry_btn.setEnabled(False)
        btn_row.addWidget(self.retry_btn)

        self.hire_btn = QPushButton("Hire! ✓")
        self.hire_btn.setStyleSheet(
            "background: #238636; color: white; border-radius: 4px; "
            "padding: 8px 20px; font-size: 13px;"
        )
        self.hire_btn.clicked.connect(self.accept)
        self.hire_btn.setEnabled(False)
        btn_row.addWidget(self.hire_btn)
        layout.addLayout(btn_row)

        # Connect AI engine signal
        self.ai_engine.generation_ready.connect(self._on_generated)
        self.ai_engine.error_occurred.connect(self._on_error)

    def _update_salary_label(self, value: int):
        self.salary_label.setText(f"${value:,}/mo")
        for (low, high), (label, color) in TIER_LABELS.items():
            if low <= value <= high:
                self.tier_label.setText(label)
                self.tier_label.setStyleSheet(f"color: {color}; font-size: 14px;")
                break

    def _generate(self):
        self.generate_btn.setEnabled(False)
        self.generate_btn.setText("Generating...")
        self.preview_label.setText("Asking Claude to generate a personality...")
        role = self.role_combo.currentText().lower()
        salary = self.salary_slider.value()
        description = self.description_input.text()
        self.ai_engine.generate_personality(role, salary, description)

    def _on_generated(self, raw_text: str):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Personality")
        try:
            # Extract JSON from response (may have markdown fences)
            text = raw_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            data = json.loads(text.strip())

            self.generated_worker = Worker(
                name=data["name"],
                emoji=data.get("emoji", "👤"),
                role=self.role_combo.currentText().lower(),
                salary=self.salary_slider.value(),
                personality_prompt=data.get("personality_prompt", ""),
                traits=data.get("traits", []),
                catchphrase=data.get("catchphrase", ""),
                favorite_excuse=data.get("favorite_excuse", ""),
            )
            preview = (
                f"{self.generated_worker.emoji} {self.generated_worker.name} — "
                f"{self.generated_worker.tier.value.title()} {self.generated_worker.role.title()}\n\n"
                f'"{self.generated_worker.catchphrase}"\n\n'
                f"Traits: {', '.join(self.generated_worker.traits)}"
            )
            self.preview_label.setText(preview)
            self.hire_btn.setEnabled(True)
            self.retry_btn.setEnabled(True)
        except (json.JSONDecodeError, KeyError) as e:
            self.preview_label.setText(f"Failed to parse response. Try again.\n\nRaw: {raw_text[:200]}")
            self.retry_btn.setEnabled(True)

    def _on_error(self, worker_id: str, error: str):
        self.generate_btn.setEnabled(True)
        self.generate_btn.setText("Generate Personality")
        self.preview_label.setText(f"Error: {error}")
        self.retry_btn.setEnabled(True)
