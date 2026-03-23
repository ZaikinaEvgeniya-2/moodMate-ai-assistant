# Hello Desktop App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a minimal Linux desktop app that displays "Hello" in a window using Python + PyQt6.

**Architecture:** Single-file PyQt6 application with a QMainWindow containing a centered QLabel. No business logic, no tests beyond manual verification.

**Tech Stack:** Python 3, PyQt6

**Spec:** `docs/superpowers/specs/2026-03-23-hello-desktop-app-design.md`

---

## File Structure

```
moodMate-ai-assistant/
├── src/
│   └── main.py              # App entry point — window with "Hello" label
├── requirements.txt          # PyQt6 dependency
└── README.md                 # Install and run instructions
```

---

### Task 1: Create requirements.txt

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
PyQt6
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: PyQt6 installs successfully

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add PyQt6 dependency"
```

---

### Task 2: Create the Hello window app

**Files:**
- Create: `src/main.py`

- [ ] **Step 1: Create src directory**

```bash
mkdir -p src
```

- [ ] **Step 2: Write src/main.py**

```python
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MoodMate")
        self.setFixedSize(400, 300)

        label = QLabel("Hello")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(label)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the app to verify**

Run: `python src/main.py`
Expected: A 400x300 window appears titled "MoodMate" with "Hello" centered. Clicking X closes it.

- [ ] **Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: add Hello desktop window"
```

---

### Task 3: Create README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# MoodMate AI Assistant

A Linux desktop application built with Python and PyQt6.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python src/main.py
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and run instructions"
```
