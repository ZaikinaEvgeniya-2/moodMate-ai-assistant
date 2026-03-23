# AI Office Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PyQt6 desktop game/simulation where you manage a virtual office of AI workers with salary-driven personalities, powered by Claude CLI.

**Architecture:** Pure PyQt6 app with room-based office view. Workers are data models rendered as clickable cards inside room containers. Claude CLI spawned via QProcess for personality generation and task execution. State persisted to JSON files in `data/`.

**Tech Stack:** Python 3, PyQt6, Claude CLI (subprocess via QProcess), JSON persistence

**Spec:** `docs/superpowers/specs/2026-03-23-ai-office-simulator-design.md`

---

### Task 0: Project Setup (pytest config, .gitignore)

**Files:**
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Create pytest.ini**

```ini
# pytest.ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 2: Create tests/__init__.py**

```python
# tests/__init__.py
```

(Empty file to make tests a package)

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
data/
.superpowers/
*.pyc
```

- [ ] **Step 4: Commit**

```bash
git add pytest.ini tests/__init__.py .gitignore
git commit -m "chore: add pytest config and .gitignore"
```

---

### Task 1: Worker Data Model

**Files:**
- Create: `src/worker.py`
- Create: `tests/test_worker.py`

- [ ] **Step 1: Write failing tests for Worker model**

```python
# tests/test_worker.py
import pytest
from src.worker import Worker, SalaryTier


def test_worker_creation():
    w = Worker(
        name="Alex",
        emoji="👨‍💻",
        role="developer",
        salary=1200,
        personality_prompt="You are Alex...",
        traits=["hardworking", "polite", "focused"],
        catchphrase="Consider it done!",
        favorite_excuse="N/A",
    )
    assert w.name == "Alex"
    assert w.salary == 1200
    assert w.status == "idle"
    assert w.current_room == "workspace"


def test_salary_tier_star():
    w = Worker(name="A", emoji="😀", role="dev", salary=1000,
               personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    assert w.tier == SalaryTier.STAR


def test_salary_tier_decent():
    w = Worker(name="A", emoji="😀", role="dev", salary=500,
               personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    assert w.tier == SalaryTier.DECENT


def test_salary_tier_mediocre():
    w = Worker(name="A", emoji="😀", role="dev", salary=300,
               personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    assert w.tier == SalaryTier.MEDIOCRE


def test_salary_tier_lazy():
    w = Worker(name="A", emoji="😀", role="dev", salary=50,
               personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    assert w.tier == SalaryTier.LAZY


def test_worker_to_dict():
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="You are Alex...", traits=["hardworking"],
               catchphrase="Done!", favorite_excuse="N/A")
    d = w.to_dict()
    assert d["name"] == "Alex"
    assert d["salary"] == 1200
    assert d["tier"] == "star"
    assert d["status"] == "idle"
    assert "id" in d


def test_worker_from_dict():
    data = {
        "id": "alex-001",
        "name": "Alex",
        "emoji": "👨‍💻",
        "role": "developer",
        "salary": 1200,
        "personality_prompt": "You are Alex...",
        "traits": ["hardworking"],
        "catchphrase": "Done!",
        "favorite_excuse": "N/A",
        "status": "idle",
        "current_room": "workspace",
    }
    w = Worker.from_dict(data)
    assert w.id == "alex-001"
    assert w.name == "Alex"
    assert w.tier == SalaryTier.STAR


def test_room_assignment_from_status():
    w = Worker(name="A", emoji="😀", role="dev", salary=100,
               personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    assert w.current_room == "workspace"
    w.status = "in_kitchen"
    assert w.current_room == "kitchen"
    w.status = "wandering"
    assert w.current_room == "hallway"
    w.status = "working"
    assert w.current_room == "workspace"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -m pytest tests/test_worker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.worker'`

- [ ] **Step 3: Implement Worker model**

```python
# src/worker.py
import uuid
from enum import Enum


class SalaryTier(Enum):
    STAR = "star"
    DECENT = "decent"
    MEDIOCRE = "mediocre"
    LAZY = "lazy"


STATUS_TO_ROOM = {
    "idle": "workspace",
    "received_task": "workspace",
    "working": "workspace",
    "done": "workspace",
    "partially_done": "workspace",
    "on_break": "kitchen",
    "in_kitchen": "kitchen",
    "wandering": "hallway",
    "making_excuses": "hallway",
}


class Worker:
    def __init__(self, name: str, emoji: str, role: str, salary: int,
                 personality_prompt: str, traits: list[str], catchphrase: str,
                 favorite_excuse: str, worker_id: str | None = None,
                 status: str = "idle"):
        self.id = worker_id or f"{name.lower()}-{uuid.uuid4().hex[:6]}"
        self.name = name
        self.emoji = emoji
        self.role = role
        self.salary = salary
        self.personality_prompt = personality_prompt
        self.traits = traits
        self.catchphrase = catchphrase
        self.favorite_excuse = favorite_excuse
        self._status = status

    @property
    def tier(self) -> SalaryTier:
        if self.salary >= 1000:
            return SalaryTier.STAR
        elif self.salary >= 500:
            return SalaryTier.DECENT
        elif self.salary >= 200:
            return SalaryTier.MEDIOCRE
        else:
            return SalaryTier.LAZY

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str):
        self._status = value

    @property
    def current_room(self) -> str:
        return STATUS_TO_ROOM.get(self._status, "workspace")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "emoji": self.emoji,
            "role": self.role,
            "salary": self.salary,
            "tier": self.tier.value,
            "personality_prompt": self.personality_prompt,
            "traits": self.traits,
            "catchphrase": self.catchphrase,
            "favorite_excuse": self.favorite_excuse,
            "status": self._status,
            "current_room": self.current_room,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Worker":
        return cls(
            name=data["name"],
            emoji=data["emoji"],
            role=data["role"],
            salary=data["salary"],
            personality_prompt=data["personality_prompt"],
            traits=data["traits"],
            catchphrase=data["catchphrase"],
            favorite_excuse=data["favorite_excuse"],
            worker_id=data.get("id"),
            status=data.get("status", "idle"),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -m pytest tests/test_worker.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/worker.py tests/test_worker.py
git commit -m "feat: add Worker data model with salary tiers and room assignment"
```

---

### Task 2: Worker Manager (Persistence)

**Files:**
- Create: `src/worker_manager.py`
- Create: `tests/test_worker_manager.py`

- [ ] **Step 1: Write failing tests for WorkerManager**

```python
# tests/test_worker_manager.py
import json
import pytest
from pathlib import Path
from src.worker import Worker
from src.worker_manager import WorkerManager


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def manager(tmp_data_dir):
    return WorkerManager(data_dir=tmp_data_dir)


def test_add_worker(manager):
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="You are Alex", traits=["focused"],
               catchphrase="Done!", favorite_excuse="N/A")
    manager.add_worker(w)
    assert len(manager.workers) == 1
    assert manager.workers[0].name == "Alex"


def test_add_worker_creates_directory(manager, tmp_data_dir):
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="prompt", traits=[], catchphrase="", favorite_excuse="")
    manager.add_worker(w)
    worker_dir = tmp_data_dir / "workers" / w.id
    assert worker_dir.exists()


def test_save_and_load(manager, tmp_data_dir):
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="prompt", traits=["a"], catchphrase="c", favorite_excuse="e")
    manager.add_worker(w)
    manager.save()

    manager2 = WorkerManager(data_dir=tmp_data_dir)
    manager2.load()
    assert len(manager2.workers) == 1
    assert manager2.workers[0].name == "Alex"
    assert manager2.workers[0].salary == 1200


def test_remove_worker(manager, tmp_data_dir):
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="prompt", traits=[], catchphrase="", favorite_excuse="")
    manager.add_worker(w)
    worker_dir = tmp_data_dir / "workers" / w.id
    assert worker_dir.exists()

    manager.remove_worker(w.id)
    assert len(manager.workers) == 0
    assert not worker_dir.exists()


def test_get_worker_by_id(manager):
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="prompt", traits=[], catchphrase="", favorite_excuse="")
    manager.add_worker(w)
    found = manager.get_worker(w.id)
    assert found is not None
    assert found.name == "Alex"


def test_total_salary(manager):
    w1 = Worker(name="A", emoji="😀", role="dev", salary=1200,
                personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    w2 = Worker(name="B", emoji="😀", role="dev", salary=100,
                personality_prompt="", traits=[], catchphrase="", favorite_excuse="")
    manager.add_worker(w1)
    manager.add_worker(w2)
    assert manager.total_salary == 1300


def test_save_chat_and_load_chat(manager, tmp_data_dir):
    w = Worker(name="Alex", emoji="👨‍💻", role="developer", salary=1200,
               personality_prompt="prompt", traits=[], catchphrase="", favorite_excuse="")
    manager.add_worker(w)
    messages = [
        {"role": "user", "content": "Fix the bug"},
        {"role": "worker", "content": "On it!"},
    ]
    manager.save_chat(w.id, messages)

    loaded = manager.load_chat(w.id)
    assert len(loaded) == 2
    assert loaded[0]["content"] == "Fix the bug"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_worker_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.worker_manager'`

- [ ] **Step 3: Implement WorkerManager**

```python
# src/worker_manager.py
import json
import shutil
from pathlib import Path
from src.worker import Worker


class WorkerManager:
    def __init__(self, data_dir: Path | str = "data"):
        self.data_dir = Path(data_dir)
        self.workers: list[Worker] = []

    def add_worker(self, worker: Worker):
        self.workers.append(worker)
        worker_dir = self.data_dir / "workers" / worker.id
        worker_dir.mkdir(parents=True, exist_ok=True)
        self.save()

    def remove_worker(self, worker_id: str):
        self.workers = [w for w in self.workers if w.id != worker_id]
        worker_dir = self.data_dir / "workers" / worker_id
        if worker_dir.exists():
            shutil.rmtree(worker_dir)
        chat_file = self.data_dir / "chat_history" / f"{worker_id}.json"
        if chat_file.exists():
            chat_file.unlink()
        self.save()

    def get_worker(self, worker_id: str) -> Worker | None:
        for w in self.workers:
            if w.id == worker_id:
                return w
        return None

    @property
    def total_salary(self) -> int:
        return sum(w.salary for w in self.workers)

    def save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        office_file = self.data_dir / "office.json"
        data = {"workers": [w.to_dict() for w in self.workers]}
        office_file.write_text(json.dumps(data, indent=2))

    def load(self):
        office_file = self.data_dir / "office.json"
        if not office_file.exists():
            self.workers = []
            return
        data = json.loads(office_file.read_text())
        self.workers = [Worker.from_dict(w) for w in data.get("workers", [])]

    def save_chat(self, worker_id: str, messages: list[dict]):
        chat_dir = self.data_dir / "chat_history"
        chat_dir.mkdir(parents=True, exist_ok=True)
        chat_file = chat_dir / f"{worker_id}.json"
        chat_file.write_text(json.dumps({"messages": messages}, indent=2))

    def load_chat(self, worker_id: str) -> list[dict]:
        chat_file = self.data_dir / "chat_history" / f"{worker_id}.json"
        if not chat_file.exists():
            return []
        data = json.loads(chat_file.read_text())
        return data.get("messages", [])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_worker_manager.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/worker_manager.py tests/test_worker_manager.py
git commit -m "feat: add WorkerManager with JSON persistence and chat history"
```

---

### Task 3: AI Engine (Claude CLI Integration)

**Files:**
- Create: `src/ai_engine.py`
- Create: `tests/test_ai_engine.py`

- [ ] **Step 1: Write failing tests for AIEngine**

Note: These tests mock QProcess since we can't depend on Claude CLI in tests.

```python
# tests/test_ai_engine.py
import pytest
from unittest.mock import MagicMock, patch
from src.ai_engine import AIEngine


def test_build_generate_command():
    engine = AIEngine()
    cmd = engine._build_generate_command(role="developer", salary=1200, description="good at Python")
    assert "claude" in cmd[0] or cmd[0].endswith("claude")
    assert "--print" in cmd
    # The prompt should mention role, salary, description
    prompt_arg = cmd[-1]
    assert "developer" in prompt_arg
    assert "1200" in prompt_arg
    assert "good at Python" in prompt_arg


def test_build_task_command():
    engine = AIEngine()
    cmd = engine._build_task_command(
        personality_prompt="You are Alex, a hard worker.",
        working_dir="/tmp/test_worker",
        message="Fix the login bug",
    )
    assert "--print" in cmd
    assert "--system-prompt" in cmd
    prompt_idx = cmd.index("--system-prompt")
    assert cmd[prompt_idx + 1] == "You are Alex, a hard worker."
    assert "Fix the login bug" in cmd[-1]


def test_build_task_command_includes_allowedtools():
    engine = AIEngine()
    cmd = engine._build_task_command(
        personality_prompt="You are Alex.",
        working_dir="/tmp/test",
        message="Do something",
    )
    # Should include --allowedTools to restrict Claude to file operations
    assert "--allowedTools" in cmd
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai_engine.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ai_engine'`

- [ ] **Step 3: Implement AIEngine**

```python
# src/ai_engine.py
import shutil
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal


class AIEngine(QObject):
    """Manages Claude CLI subprocesses for personality generation and task execution."""

    response_ready = pyqtSignal(str, str)  # (worker_id, response_text)
    generation_ready = pyqtSignal(str)  # (generated_json_text)
    error_occurred = pyqtSignal(str, str)  # (worker_id, error_message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._claude_path = shutil.which("claude") or "claude"
        self._processes: dict[str, QProcess] = {}

    def _build_generate_command(self, role: str, salary: int, description: str) -> list[str]:
        prompt = (
            f"Generate a worker personality for a {role} with salary ${salary}. "
            f"Additional info: {description}. "
            "Include: name, emoji (single emoji for avatar), 3 personality traits, "
            "work style, favorite excuse for not working, catchphrase. "
            "Return ONLY valid JSON with keys: name, emoji, traits (array of 3 strings), "
            "catchphrase, favorite_excuse, personality_prompt (a 2-3 sentence system prompt "
            "describing this character's personality and work ethic for future interactions)."
        )
        return [self._claude_path, "--print", prompt]

    def _build_task_command(self, personality_prompt: str, working_dir: str,
                            message: str) -> list[str]:
        return [
            self._claude_path, "--print",
            "--system-prompt", personality_prompt,
            "--allowedTools", "Read,Write,Edit,Glob,Grep",
            "--working-dir", working_dir,
            message,
        ]

    def generate_personality(self, role: str, salary: int, description: str = ""):
        cmd = self._build_generate_command(role, salary, description)
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def on_finished(exit_code, exit_status):
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if exit_code == 0:
                self.generation_ready.emit(output)
            else:
                self.error_occurred.emit("", f"Generation failed: {output}")
            process.deleteLater()

        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])

    def run_task(self, worker_id: str, personality_prompt: str,
                 working_dir: str, message: str):
        cmd = self._build_task_command(personality_prompt, working_dir, message)
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._processes[worker_id] = process

        def on_finished(exit_code, exit_status):
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if exit_code == 0:
                self.response_ready.emit(worker_id, output)
            else:
                self.error_occurred.emit(worker_id, f"Task failed: {output}")
            self._processes.pop(worker_id, None)
            process.deleteLater()

        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])

    def is_worker_busy(self, worker_id: str) -> bool:
        return worker_id in self._processes
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai_engine.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/ai_engine.py tests/test_ai_engine.py
git commit -m "feat: add AIEngine for Claude CLI subprocess management"
```

---

### Task 4: Personality & Behavior System

**Files:**
- Create: `src/personality.py`
- Create: `tests/test_personality.py`

- [ ] **Step 1: Write failing tests for behavior logic**

```python
# tests/test_personality.py
import pytest
import random
from src.worker import Worker, SalaryTier
from src.personality import BehaviorEngine


def make_worker(salary: int, status: str = "idle") -> Worker:
    w = Worker(name="Test", emoji="😀", role="developer", salary=salary,
               personality_prompt="", traits=[], catchphrase="", favorite_excuse="Tired")
    w.status = status
    return w


def test_star_receives_task():
    engine = BehaviorEngine()
    w = make_worker(1200, "received_task")
    random.seed(42)
    new_status, delay = engine.decide_next_status(w)
    assert new_status == "working"
    assert delay == 0


def test_lazy_receives_task_goes_to_kitchen_or_excuses():
    engine = BehaviorEngine()
    results = set()
    for seed in range(100):
        w = make_worker(50, "received_task")
        random.seed(seed)
        new_status, delay = engine.decide_next_status(w)
        results.add(new_status)
    # Should see both kitchen and excuses outcomes
    assert "in_kitchen" in results
    assert "making_excuses" in results


def test_decent_mostly_works():
    engine = BehaviorEngine()
    w = make_worker(700, "received_task")
    new_status, delay = engine.decide_next_status(w)
    assert new_status == "working"


def test_mediocre_may_delay():
    engine = BehaviorEngine()
    results = set()
    for seed in range(100):
        w = make_worker(300, "received_task")
        random.seed(seed)
        new_status, delay = engine.decide_next_status(w)
        results.add(new_status)
    # Should sometimes work, sometimes delay
    assert "working" in results


def test_kitchen_timer_returns():
    engine = BehaviorEngine()
    w = make_worker(50, "in_kitchen")
    new_status, delay = engine.decide_next_status(w)
    assert new_status in ("wandering", "working", "idle")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_personality.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.personality'`

- [ ] **Step 3: Implement BehaviorEngine**

```python
# src/personality.py
import random
from src.worker import Worker, SalaryTier


class BehaviorEngine:
    """Decides worker status transitions based on salary tier and randomness."""

    def decide_next_status(self, worker: Worker) -> tuple[str, int]:
        """Returns (new_status, delay_seconds). delay=0 means immediate."""
        tier = worker.tier
        status = worker.status

        if status == "received_task":
            return self._on_received_task(tier)
        elif status == "in_kitchen":
            return self._on_in_kitchen(tier)
        elif status == "making_excuses":
            return self._on_making_excuses(tier)
        elif status == "wandering":
            return self._on_wandering(tier)
        elif status == "on_break":
            return self._on_break(tier)
        else:
            return (status, 0)

    def should_take_break(self, worker: Worker) -> bool:
        """Check if a working worker should take a break mid-task."""
        tier = worker.tier
        if tier == SalaryTier.STAR:
            return False
        elif tier == SalaryTier.DECENT:
            return random.random() < 0.3
        elif tier == SalaryTier.MEDIOCRE:
            return random.random() < 0.5
        else:  # LAZY
            return random.random() < 0.7

    def _on_received_task(self, tier: SalaryTier) -> tuple[str, int]:
        if tier == SalaryTier.STAR:
            return ("working", 0)
        elif tier == SalaryTier.DECENT:
            return ("working", 0)
        elif tier == SalaryTier.MEDIOCRE:
            if random.random() < 0.4:
                return ("on_break", random.randint(10, 20))
            return ("working", 0)
        else:  # LAZY
            if random.random() < 0.7:
                return ("in_kitchen", random.randint(30, 60))
            return ("making_excuses", random.randint(15, 30))

    def _on_in_kitchen(self, tier: SalaryTier) -> tuple[str, int]:
        if tier == SalaryTier.LAZY:
            if random.random() < 0.5:
                return ("wandering", random.randint(15, 30))
            return ("working", 0)
        return ("working", 0)

    def _on_making_excuses(self, tier: SalaryTier) -> tuple[str, int]:
        if random.random() < 0.4:
            return ("working", 0)
        return ("in_kitchen", random.randint(20, 40))

    def _on_wandering(self, tier: SalaryTier) -> tuple[str, int]:
        if random.random() < 0.3:
            return ("working", 0)
        return ("idle", 0)

    def _on_break(self, tier: SalaryTier) -> tuple[str, int]:
        return ("working", 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_personality.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/personality.py tests/test_personality.py
git commit -m "feat: add BehaviorEngine for salary-based status transitions"
```

---

### Task 5: Worker Widget (Visual Card)

**Files:**
- Create: `src/worker_widget.py`

- [ ] **Step 1: Create WorkerWidget**

```python
# src/worker_widget.py
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
```

- [ ] **Step 2: Smoke test by running the app**

Create a temporary test script to verify the widget renders. Visual verification — run and confirm the card looks correct.

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from src.worker import Worker
from src.worker_widget import WorkerWidget
app = QApplication(sys.argv)
w = Worker(name='Alex', emoji='👨‍💻', role='developer', salary=1200,
           personality_prompt='', traits=[], catchphrase='', favorite_excuse='')
w.status = 'working'
win = QWidget()
layout = QVBoxLayout(win)
ww = WorkerWidget(w)
ww.set_task_text('Fix login bug')
layout.addWidget(ww)
win.setStyleSheet('background: #0d1117;')
win.show()
app.exec()
"`

Expected: A dark-themed card appears showing "👨‍💻 Alex", green "● Working" status, "$1,200/mo", "Task: Fix login bug"

- [ ] **Step 3: Commit**

```bash
git add src/worker_widget.py
git commit -m "feat: add WorkerWidget card component"
```

---

### Task 6: Office View (Room-Based Floor Plan)

**Files:**
- Create: `src/office_view.py`

- [ ] **Step 1: Create OfficeView**

```python
# src/office_view.py
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
```

- [ ] **Step 2: Smoke test the office view**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "
import sys
from PyQt6.QtWidgets import QApplication
from src.worker import Worker
from src.office_view import OfficeView
app = QApplication(sys.argv)
view = OfficeView()
view.setStyleSheet('background: #0d1117; color: white;')
view.resize(800, 600)
w1 = Worker(name='Alex', emoji='👨‍💻', role='developer', salary=1200,
            personality_prompt='', traits=[], catchphrase='', favorite_excuse='')
w1.status = 'working'
w2 = Worker(name='Marina', emoji='🍵', role='writer', salary=100,
            personality_prompt='', traits=[], catchphrase='', favorite_excuse='')
w2.status = 'in_kitchen'
view.add_worker(w1)
view.add_worker(w2)
view.update_status_bar([w1, w2], 1300)
view.show()
app.exec()
"`

Expected: Office with 4 rooms visible. Alex in Workspace (green), Marina in Kitchen (orange). Status bar shows counts and total salary.

- [ ] **Step 3: Commit**

```bash
git add src/office_view.py
git commit -m "feat: add OfficeView with room-based floor plan layout"
```

---

### Task 7: Chat Dialog

**Files:**
- Create: `src/chat_dialog.py`

- [ ] **Step 1: Create ChatDialog**

```python
# src/chat_dialog.py
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)
from src.worker import Worker
from src.worker_widget import STATUS_COLORS, STATUS_LABELS


class ChatDialog(QDialog):
    message_sent = pyqtSignal(str, str)  # (worker_id, message)
    fire_requested = pyqtSignal(str)  # worker_id

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

        # Chat area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #333; border-radius: 4px; }")
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.chat_widget)
        layout.addWidget(scroll)

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
        send_btn.clicked.connect(self._send_message)
        input_row.addWidget(send_btn)
        layout.addLayout(input_row)

        # Fire button
        fire_btn = QPushButton("Fire 🔥")
        fire_btn.setStyleSheet(
            "background: #3a1515; color: #f44336; border: 1px solid #f44336; "
            "border-radius: 4px; padding: 6px 16px; font-size: 11px;"
        )
        fire_btn.clicked.connect(lambda: self.fire_requested.emit(self.worker.id))
        layout.addWidget(fire_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _add_message(self, role: str, content: str):
        if role == "user":
            label = QLabel(f"You: {content}")
            label.setStyleSheet("color: #64ffda; font-size: 12px; padding: 4px;")
        else:
            label = QLabel(f"{self.worker.name}: {content}")
            label.setStyleSheet("color: #ccc; font-size: 12px; padding: 4px;")
        label.setWordWrap(True)
        self.chat_layout.addWidget(label)

    def add_response(self, content: str):
        self._add_message("worker", content)

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self._add_message("user", text)
        self.message_sent.emit(self.worker.id, text)
```

- [ ] **Step 2: Smoke test the chat dialog**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "
import sys
from PyQt6.QtWidgets import QApplication
from src.worker import Worker
from src.chat_dialog import ChatDialog
app = QApplication(sys.argv)
w = Worker(name='Alex', emoji='👨‍💻', role='developer', salary=1200,
           personality_prompt='', traits=['hardworking', 'polite', 'focused'],
           catchphrase='Consider it done!', favorite_excuse='N/A')
w.status = 'working'
msgs = [{'role': 'user', 'content': 'Fix the login bug'},
        {'role': 'worker', 'content': 'On it, boss! Looking at auth.py now...'}]
dlg = ChatDialog(w, msgs)
dlg.exec()
"`

Expected: Modal dialog with Alex's info, traits badges, chat history, input field, and Fire button.

- [ ] **Step 3: Commit**

```bash
git add src/chat_dialog.py
git commit -m "feat: add ChatDialog popup with worker info, chat history, and input"
```

---

### Task 8: Hire Dialog

**Files:**
- Create: `src/hire_dialog.py`

- [ ] **Step 1: Create HireDialog**

```python
# src/hire_dialog.py
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
```

- [ ] **Step 2: Smoke test the hire dialog**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "
import sys
from PyQt6.QtWidgets import QApplication
from src.ai_engine import AIEngine
from src.hire_dialog import HireDialog
app = QApplication(sys.argv)
engine = AIEngine()
dlg = HireDialog(engine)
dlg.exec()
"`

Expected: Dialog appears with role dropdown, salary slider (updates tier label live), description field, Generate button, and preview area.

- [ ] **Step 3: Commit**

```bash
git add src/hire_dialog.py
git commit -m "feat: add HireDialog with role selection, salary slider, and AI personality generation"
```

---

### Task 9: Main Window (Wiring Everything Together)

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Rewrite main.py to wire all components**

```python
# src/main.py
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from src.ai_engine import AIEngine
from src.chat_dialog import ChatDialog
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
            # Worker procrastinates first
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
            self._run_task(worker_id, original_message)
        elif delay > 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._after_delay(worker_id, original_message))
            timer.start(delay * 1000)
            self._pending_timers[worker_id] = timer
        else:
            # Worker gave up, add a snarky message
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
        working_dir = str(DATA_DIR / "workers" / worker.id)
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
```

- [ ] **Step 2: Run the full app**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python src/main.py`

Expected: App launches with empty office. "Hire Worker" button visible. Clicking it opens the hire dialog.

- [ ] **Step 3: Run all tests to make sure nothing broke**

Run: `python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add src/main.py
git commit -m "feat: wire MainWindow with office view, hiring, chat, and AI task execution"
```

---

### Task 11: End-to-End Manual Test

**Files:** None (testing only)

- [ ] **Step 1: Start the app**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python src/main.py`

- [ ] **Step 2: Test hiring a Star worker**

1. Click "+ Hire Worker"
2. Select role: Developer
3. Set salary to $1200 (Star tier)
4. Type description: "expert in Python"
5. Click "Generate Personality"
6. Wait for Claude CLI to generate — verify preview shows name, emoji, traits
7. Click "Hire!"
8. Verify worker appears in Workspace room

- [ ] **Step 3: Test hiring a Lazy worker**

1. Click "+ Hire Worker"
2. Select role: Writer
3. Set salary to $50 (Lazy tier)
4. Click "Generate Personality"
5. Verify preview shows lazy personality traits
6. Click "Hire!"
7. Verify worker appears in Workspace

- [ ] **Step 4: Test giving a task to the Star worker**

1. Click on the Star worker card
2. Chat dialog opens — verify info and traits display correctly
3. Type: "Create a hello.py file that prints Hello World"
4. Verify worker status changes to "Working"
5. Wait for response — should be professional and actually create the file
6. Check `data/workers/{worker_id}/hello.py` exists

- [ ] **Step 5: Test giving a task to the Lazy worker**

1. Click on the Lazy worker card
2. Type: "Write a poem about Python"
3. Verify worker moves to Kitchen or starts making excuses
4. Wait — worker should eventually produce minimal/funny output
5. Observe status changes in the office view

- [ ] **Step 6: Test firing a worker**

1. Open chat with any worker
2. Click "Fire 🔥"
3. Confirm in dialog
4. Verify worker disappears from office
5. Verify data directory is cleaned up

- [ ] **Step 7: Test persistence**

1. Close the app
2. Reopen: `python src/main.py`
3. Verify remaining workers are still visible with correct room placement
