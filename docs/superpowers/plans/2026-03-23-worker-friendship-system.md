# Worker Friendship System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Workers form friendships by sharing non-workspace rooms, follow friends around, and have AI-generated conversations visible to the user.

**Architecture:** New `FriendshipManager` owns all friendship state and persistence. MainWindow runs a 10-second tick timer for co-location detection, friendship growth, and conversation triggers. Follow-friend logic lives in MainWindow (needs `_pending_messages` access). New `FriendGroupWidget` and `FriendChatDialog` handle the UI for chatting friends.

**Tech Stack:** Python 3, PyQt6, JSON persistence, existing AIEngine/AIProvider for conversation generation.

**Spec:** `docs/superpowers/specs/2026-03-23-worker-friendship-system-design.md`

---

### Task 1: Add `chatting` status and `_room_override` to Worker model

**Files:**
- Modify: `src/worker.py:12-22` (STATUS_TO_ROOM)
- Modify: `src/worker.py:25-96` (Worker class)
- Modify: `src/worker_widget.py:6-28` (STATUS_COLORS, STATUS_LABELS)

- [ ] **Step 1: Add `chatting` to STATUS_TO_ROOM**

In `src/worker.py`, add `"chatting": "kitchen"` as fallback default to the `STATUS_TO_ROOM` dict:

```python
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
    "chatting": "kitchen",
}
```

- [ ] **Step 2: Add `_room_override` field to Worker.__init__**

In `src/worker.py:29`, add `self._room_override: str | None = None` after `self.working_dir = working_dir`:

```python
    def __init__(self, name: str, emoji: str, role: str, salary: int,
                 personality_prompt: str, traits: list[str], catchphrase: str,
                 favorite_excuse: str, worker_id: str | None = None,
                 status: str = "idle", working_dir: str = ""):
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
        self.working_dir = working_dir
        self._room_override: str | None = None
```

- [ ] **Step 3: Update `current_room` property to check override**

Replace the `current_room` property in `src/worker.py:61-63`:

```python
    @property
    def current_room(self) -> str:
        if self._room_override:
            return self._room_override
        return STATUS_TO_ROOM.get(self._status, "workspace")
```

- [ ] **Step 4: Update status setter to clear override when leaving `chatting`**

Replace the status setter in `src/worker.py:57-59`:

```python
    @status.setter
    def status(self, value: str):
        if self._status == "chatting" and value != "chatting":
            self._room_override = None
        self._status = value
```

- [ ] **Step 5: Add `chatting` to STATUS_COLORS and STATUS_LABELS**

In `src/worker_widget.py`, add entries to both dicts:

```python
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
```

- [ ] **Step 6: Add `chatting` to BehaviorEngine awareness**

In `src/personality.py`, add a case to `decide_next_status` so it doesn't override chatting status. Add after the `elif status == "on_break":` block (line 21):

```python
        elif status == "chatting":
            return (status, 0)  # Don't override — FriendshipManager controls this
```

- [ ] **Step 7: Add `chatting` to Chef's `_SLACKING_STATUSES`**

In `src/main.py:278`, update the set:

```python
    _SLACKING_STATUSES = {"on_break", "in_kitchen", "wandering", "making_excuses", "chatting"}
```

- [ ] **Step 8: Verify the app launches without errors**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.worker import Worker, STATUS_TO_ROOM; from src.worker_widget import STATUS_COLORS, STATUS_LABELS; w = Worker('Test', '🧪', 'dev', 500, '', [], '', ''); w._room_override = 'hallway'; w.status = 'chatting'; assert w.current_room == 'hallway'; w.status = 'idle'; assert w._room_override is None; assert w.current_room == 'workspace'; print('All checks pass')"`

Expected: `All checks pass`

- [ ] **Step 9: Commit**

```bash
git add src/worker.py src/worker_widget.py src/personality.py src/main.py
git commit -m "feat: add chatting status with room override support"
```

---

### Task 2: Create FriendshipManager with persistence

**Files:**
- Create: `src/friendship_manager.py`

- [ ] **Step 1: Create `src/friendship_manager.py` with core class**

```python
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("friendship_manager")

# Friendship level -> follow chance (0.0 to 1.0)
FOLLOW_CHANCES = {1: 0.10, 2: 0.25, 3: 0.40, 4: 0.60, 5: 0.80}

# Friendship level -> chat duration in seconds
CHAT_DURATIONS = {1: 15, 2: 22, 3: 30, 4: 37, 5: 45}

MAX_LEVEL = 5
CONVERSATION_COOLDOWN = 60  # seconds between conversations for a pair


def _pair_key(id_a: str, id_b: str) -> str:
    """Sorted pipe-delimited key for a worker pair."""
    return "|".join(sorted([id_a, id_b]))


class FriendshipManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.friendships: dict[str, int] = {}  # "id_a|id_b" -> level
        self._last_conversation: dict[str, float] = {}  # "id_a|id_b" -> timestamp
        self._chatting_pairs: dict[str, tuple[str, str]] = {}  # "id_a|id_b" -> (id_a, id_b)
        self._pre_chat_status: dict[str, str] = {}  # worker_id -> status before chatting

    def get_level(self, id_a: str, id_b: str) -> int:
        return self.friendships.get(_pair_key(id_a, id_b), 0)

    def increase_friendship(self, id_a: str, id_b: str) -> bool:
        """Increase friendship by 1. Returns True if level changed."""
        key = _pair_key(id_a, id_b)
        current = self.friendships.get(key, 0)
        if current >= MAX_LEVEL:
            return False
        self.friendships[key] = current + 1
        logger.info(f"Friendship {key}: {current} -> {current + 1}")
        return True

    def get_friends(self, worker_id: str) -> list[tuple[str, int]]:
        """Return list of (friend_id, level) for a worker."""
        result = []
        for key, level in self.friendships.items():
            ids = key.split("|")
            if worker_id in ids:
                friend_id = ids[0] if ids[1] == worker_id else ids[1]
                result.append((friend_id, level))
        return result

    def get_friend_count(self, worker_id: str) -> int:
        return len(self.get_friends(worker_id))

    def is_chatting(self, worker_id: str) -> bool:
        """Check if worker is currently in a friend conversation."""
        for pair_ids in self._chatting_pairs.values():
            if worker_id in pair_ids:
                return True
        return False

    def can_start_conversation(self, id_a: str, id_b: str) -> bool:
        """Check cooldown and that neither worker is already chatting."""
        if self.is_chatting(id_a) or self.is_chatting(id_b):
            return False
        key = _pair_key(id_a, id_b)
        last = self._last_conversation.get(key, 0)
        return (datetime.now().timestamp() - last) >= CONVERSATION_COOLDOWN

    def start_conversation(self, id_a: str, id_b: str, pre_status_a: str, pre_status_b: str):
        """Mark a pair as chatting. Store their pre-chat statuses."""
        key = _pair_key(id_a, id_b)
        self._chatting_pairs[key] = (id_a, id_b)
        self._pre_chat_status[id_a] = pre_status_a
        self._pre_chat_status[id_b] = pre_status_b
        logger.info(f"Conversation started: {key}")

    def end_conversation(self, id_a: str, id_b: str) -> tuple[str, str]:
        """End conversation, return (pre_status_a, pre_status_b)."""
        key = _pair_key(id_a, id_b)
        self._chatting_pairs.pop(key, None)
        self._last_conversation[key] = datetime.now().timestamp()
        status_a = self._pre_chat_status.pop(id_a, "idle")
        status_b = self._pre_chat_status.pop(id_b, "idle")
        logger.info(f"Conversation ended: {key}")
        return status_a, status_b

    def remove_worker(self, worker_id: str):
        """Clean up all friendship data for a removed worker."""
        keys_to_remove = [k for k in self.friendships if worker_id in k.split("|")]
        for key in keys_to_remove:
            del self.friendships[key]
            self._chatting_pairs.pop(key, None)
            self._last_conversation.pop(key, None)
        self._pre_chat_status.pop(worker_id, None)
        self.save()

    # --- Persistence ---

    def save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        filepath = self.data_dir / "friendships.json"
        data = {"friendships": self.friendships}
        filepath.write_text(json.dumps(data, indent=2))

    def load(self):
        filepath = self.data_dir / "friendships.json"
        if not filepath.exists():
            self.friendships = {}
            return
        data = json.loads(filepath.read_text())
        self.friendships = data.get("friendships", {})

    def save_conversation(self, id_a: str, id_b: str, lines: list[dict]):
        """Save a conversation to data/conversations/{sorted_ids}.json"""
        conv_dir = self.data_dir / "conversations"
        conv_dir.mkdir(parents=True, exist_ok=True)
        key = _pair_key(id_a, id_b)
        filename = key.replace("|", "_") + ".json"
        filepath = conv_dir / filename

        existing = []
        if filepath.exists():
            data = json.loads(filepath.read_text())
            existing = data.get("conversations", [])

        existing.append({
            "timestamp": datetime.now().isoformat(),
            "lines": lines,
        })
        filepath.write_text(json.dumps({"conversations": existing}, indent=2))

    def load_conversations(self, id_a: str, id_b: str) -> list[dict]:
        """Load all conversations between a pair."""
        key = _pair_key(id_a, id_b)
        filename = key.replace("|", "_") + ".json"
        filepath = self.data_dir / "conversations" / filename
        if not filepath.exists():
            return []
        data = json.loads(filepath.read_text())
        return data.get("conversations", [])
```

- [ ] **Step 2: Verify the module imports correctly**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.friendship_manager import FriendshipManager, _pair_key, FOLLOW_CHANCES, CHAT_DURATIONS; fm = FriendshipManager(Path('/tmp/test_fm')); assert _pair_key('bob', 'alice') == 'alice|bob'; assert fm.get_level('a', 'b') == 0; fm.increase_friendship('b', 'a'); assert fm.get_level('a', 'b') == 1; print('All checks pass')" -c "from pathlib import Path; exec(open('/dev/stdin').read())" 2>/dev/null || python -c "
from pathlib import Path
from src.friendship_manager import FriendshipManager, _pair_key, FOLLOW_CHANCES, CHAT_DURATIONS
fm = FriendshipManager(Path('/tmp/test_fm'))
assert _pair_key('bob', 'alice') == 'alice|bob'
assert fm.get_level('a', 'b') == 0
fm.increase_friendship('b', 'a')
assert fm.get_level('a', 'b') == 1
assert fm.get_friends('a') == [('b', 1)]
print('All checks pass')
"`

Expected: `All checks pass`

- [ ] **Step 3: Commit**

```bash
git add src/friendship_manager.py
git commit -m "feat: add FriendshipManager with persistence and conversation storage"
```

---

### Task 3: Add `build_conversation_command` to AIProvider

**Files:**
- Modify: `src/providers/__init__.py:5-16` (AIProvider class)
- Modify: `src/providers/opencode_provider.py:34-47` (add new method)
- Modify: `src/providers/claude_provider.py` (add new method)

- [ ] **Step 1: Add abstract method to AIProvider**

In `src/providers/__init__.py`, add a new abstract method after `build_task_command`:

```python
    @abstractmethod
    def build_conversation_command(self, personality_a: str, name_a: str,
                                    personality_b: str, name_b: str) -> list[str]:
        """Build CLI command for generating a friend conversation."""
        ...
```

- [ ] **Step 2: Implement in OpencodeProvider**

In `src/providers/opencode_provider.py`, add after `build_task_command`:

```python
    def build_conversation_command(self, personality_a: str, name_a: str,
                                    personality_b: str, name_b: str) -> list[str]:
        prompt = (
            f"Generate a short funny conversation (3-4 lines) between two office workers "
            f"who are hanging out instead of working.\n\n"
            f"Worker 1 - {name_a}:\n{personality_a}\n\n"
            f"Worker 2 - {name_b}:\n{personality_b}\n\n"
            f"Return ONLY valid JSON array of objects with keys: name, text\n"
            f'Example: [{{"name": "{name_a}", "text": "hey"}}, '
            f'{{"name": "{name_b}", "text": "sup"}}]'
        )
        cmd = [self._path, "run", "-m", self._model_generate, prompt]
        logger.debug(f"[conversation] command: {cmd[:4]} + [prompt ({len(prompt)} chars)]")
        return cmd
```

- [ ] **Step 3: Implement in ClaudeProvider**

Read `src/providers/claude_provider.py` first to follow its pattern, then add the equivalent method.

- [ ] **Step 4: Add `generate_conversation` method to AIEngine**

In `src/ai_engine.py`, add a new signal and method. Add signal after line 18:

```python
    conversation_ready = pyqtSignal(str, str, str)  # (worker_id_a, worker_id_b, json_text)
```

Add method after `run_task` (after line 142):

```python
    def generate_conversation(self, worker_id_a: str, worker_id_b: str,
                               personality_a: str, name_a: str,
                               personality_b: str, name_b: str):
        """Generate a conversation between two workers."""
        cmd = self._provider.build_conversation_command(
            personality_a, name_a, personality_b, name_b
        )
        conv_key = f"conv:{worker_id_a}:{worker_id_b}"
        logger.info(f"[{conv_key}] Starting conversation generation")

        process = QProcess(self)
        process.setProcessEnvironment(self._env)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._processes[conv_key] = process

        start_time = time.monotonic()

        def on_finished(exit_code, exit_status):
            elapsed = time.monotonic() - start_time
            output = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
            logger.info(f"[{conv_key}] Finished: exit={exit_code}, elapsed={elapsed:.1f}s")
            if exit_code == 0:
                self.conversation_ready.emit(worker_id_a, worker_id_b, output)
            else:
                logger.error(f"[{conv_key}] Failed: {output[:200]}")
            self._processes.pop(conv_key, None)
            process.deleteLater()

        process.finished.connect(on_finished)
        process.start(cmd[0], cmd[1:])
        process.closeWriteChannel()

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._kill_if_running(process, conv_key))
        timer.start(PROCESS_TIMEOUT_MS)
        process.finished.connect(timer.stop)
```

- [ ] **Step 5: Verify import works**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.ai_engine import AIEngine; print('AIEngine imports OK')"`

Expected: `AIEngine imports OK`

- [ ] **Step 6: Commit**

```bash
git add src/providers/__init__.py src/providers/opencode_provider.py src/providers/claude_provider.py src/ai_engine.py
git commit -m "feat: add conversation generation to AI providers and engine"
```

---

### Task 4: Wire FriendshipManager into MainWindow — tick timer, friendship growth, follow-friend

**Files:**
- Modify: `src/main.py:1-73` (imports, __init__)
- Modify: `src/main.py:99-136` (after status change, trigger follow)

- [ ] **Step 1: Import FriendshipManager and add to MainWindow.__init__**

In `src/main.py`, add import after line 30:

```python
from src.friendship_manager import FriendshipManager, FOLLOW_CHANCES, CHAT_DURATIONS
```

In `MainWindow.__init__`, after `self.manager.load()` (line 46), add:

```python
        self.friendships = FriendshipManager(data_dir=DATA_DIR)
        self.friendships.load()
```

- [ ] **Step 2: Add friendship tick timer**

In `MainWindow.__init__`, after the chef timer setup (after line 72), add:

```python
        # Friendship tick timer — co-location detection & conversation triggers
        self._friendship_timer = QTimer(self)
        self._friendship_timer.timeout.connect(self._friendship_tick)
        self._friendship_timer.start(10_000)  # every 10 seconds
```

- [ ] **Step 3: Implement `_friendship_tick` method**

Add after `_chef_send_to_work` method (after line 323), before `_fire_worker`:

```python
    # --- Friendship system ---

    _SOCIALIZING_STATUSES = {"on_break", "in_kitchen", "wandering", "making_excuses", "chatting"}

    def _friendship_tick(self):
        """Every 10s: grow friendships for co-located workers, trigger conversations."""
        # Group workers by room (skip workspace)
        rooms: dict[str, list] = {}
        for worker in self.manager.workers:
            room = worker.current_room
            if room == "workspace":
                continue
            if worker.status not in self._SOCIALIZING_STATUSES:
                continue
            rooms.setdefault(room, []).append(worker)

        changed = False
        for room, workers in rooms.items():
            if len(workers) < 2:
                continue
            # Grow friendships for every pair
            for i, w_a in enumerate(workers):
                for w_b in workers[i + 1:]:
                    if self.friendships.increase_friendship(w_a.id, w_b.id):
                        changed = True
                    # Try to start conversation if they're friends and not already chatting
                    level = self.friendships.get_level(w_a.id, w_b.id)
                    if (level > 0
                            and w_a.status != "chatting" and w_b.status != "chatting"
                            and self.friendships.can_start_conversation(w_a.id, w_b.id)):
                        self._start_friend_conversation(w_a, w_b)

        if changed:
            self.friendships.save()
            self._refresh_friend_indicators()
```

- [ ] **Step 4: Implement `_start_friend_conversation` method**

Add right after `_friendship_tick`:

```python
    def _start_friend_conversation(self, worker_a, worker_b):
        """Initiate AI-generated conversation between two friends."""
        room = worker_a.current_room  # they're in the same room

        # Store pre-chat status and switch to chatting
        self.friendships.start_conversation(
            worker_a.id, worker_b.id, worker_a.status, worker_b.status
        )
        worker_a._room_override = room
        worker_a.status = "chatting"
        worker_b._room_override = room
        worker_b.status = "chatting"
        self.office.update_worker(worker_a)
        self.office.update_worker(worker_b)
        self._refresh_status_bar()

        # Fire AI call
        self.ai_engine.generate_conversation(
            worker_a.id, worker_b.id,
            worker_a.personality_prompt, worker_a.name,
            worker_b.personality_prompt, worker_b.name,
        )

        # Set timeout to end conversation based on friendship level
        level = self.friendships.get_level(worker_a.id, worker_b.id)
        duration = CHAT_DURATIONS.get(level, 15) * 1000
        QTimer.singleShot(
            duration,
            lambda a=worker_a.id, b=worker_b.id: self._end_friend_conversation(a, b),
        )
```

- [ ] **Step 5: Implement `_end_friend_conversation` method**

```python
    def _end_friend_conversation(self, id_a: str, id_b: str):
        """End a conversation and restore workers to pre-chat status."""
        worker_a = self.manager.get_worker(id_a)
        worker_b = self.manager.get_worker(id_b)
        if not worker_a or not worker_b:
            return
        # Only end if still chatting (chef may have already interrupted)
        if worker_a.status != "chatting" or worker_b.status != "chatting":
            return

        status_a, status_b = self.friendships.end_conversation(id_a, id_b)
        worker_a.status = status_a
        worker_b.status = status_b
        self.office.update_worker(worker_a)
        self.office.update_worker(worker_b)
        self.office.remove_friend_group(id_a, id_b)
        self._refresh_status_bar()
```

- [ ] **Step 6: Connect `conversation_ready` signal in `__init__`**

In `MainWindow.__init__`, after `self.ai_engine.error_occurred.connect(...)` (line 60), add:

```python
        self.ai_engine.conversation_ready.connect(self._on_conversation_ready)
```

- [ ] **Step 7: Implement `_on_conversation_ready` handler**

```python
    def _on_conversation_ready(self, id_a: str, id_b: str, raw_json: str):
        """Handle AI-generated conversation text."""
        import json as _json
        try:
            # Try to extract JSON array from response
            text = raw_json.strip()
            # Find the JSON array in the response
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                lines = _json.loads(text[start:end])
            else:
                lines = []
        except Exception:
            logger.warning(f"Failed to parse conversation JSON: {raw_json[:200]}")
            lines = []

        if lines:
            # Convert to our format: [{worker_id, text}, ...]
            worker_a = self.manager.get_worker(id_a)
            worker_b = self.manager.get_worker(id_b)
            if not worker_a or not worker_b:
                return
            formatted = []
            for line in lines:
                name = line.get("name", "")
                text = line.get("text", "")
                if name == worker_a.name:
                    formatted.append({"worker_id": id_a, "text": text})
                else:
                    formatted.append({"worker_id": id_b, "text": text})

            self.friendships.save_conversation(id_a, id_b, formatted)

            # Update the friend group widget with conversation snippet
            self.office.update_friend_group_conversation(id_a, id_b, formatted)
```

- [ ] **Step 8: Implement follow-friend logic**

Add this method and call it when a worker's status changes to a slacking state. Add after `_on_conversation_ready`:

```python
    def _check_follow_friend(self, worker):
        """When a worker starts slacking, maybe a friend follows them."""
        if worker.status not in self._SOCIALIZING_STATUSES:
            return
        if worker.status == "chatting":
            return

        friends = self.friendships.get_friends(worker.id)
        if not friends:
            return

        eligible = []
        for friend_id, level in friends:
            friend = self.manager.get_worker(friend_id)
            if not friend:
                continue
            if friend.status != "idle":
                continue
            if friend.id in self._pending_messages:
                continue
            # Roll the dice
            chance = FOLLOW_CHANCES.get(level, 0)
            if random.random() < chance:
                eligible.append((friend, level))

        if not eligible:
            return

        # Pick one follower (weighted by level)
        eligible.sort(key=lambda x: x[1], reverse=True)
        follower, _ = eligible[0]

        # Follow after a short delay
        target_status = worker.status
        delay = random.randint(2, 5) * 1000
        QTimer.singleShot(
            delay,
            lambda fid=follower.id, s=target_status: self._follow_friend(fid, s),
        )
```

```python
    def _follow_friend(self, follower_id: str, target_status: str):
        """Make a worker follow their friend to a room."""
        follower = self.manager.get_worker(follower_id)
        if not follower:
            return
        # Only follow if still idle and no pending task
        if follower.status != "idle" or follower.id in self._pending_messages:
            return
        follower.status = target_status
        self.office.update_worker(follower)
        self._refresh_status_bar()
        logger.info(f"{follower.name} followed a friend -> {target_status}")
```

- [ ] **Step 9: Hook `_check_follow_friend` into status change points**

In `_on_chat_message` (around line 119), after `worker.status = new_status` and `self.office.update_worker(worker)`, add:

```python
            self._check_follow_friend(worker)
```

Similarly in `_after_delay` (around line 145), after `worker.status = new_status` and `self.office.update_worker(worker)`, add:

```python
        self._check_follow_friend(worker)
```

- [ ] **Step 10: Add `_refresh_friend_indicators` placeholder**

```python
    def _refresh_friend_indicators(self):
        """Update friend count indicators on worker widgets."""
        for worker in self.manager.workers:
            count = self.friendships.get_friend_count(worker.id)
            self.office.update_friend_indicator(worker.id, count)
```

- [ ] **Step 11: Handle chef interrupting conversations**

In `_chef_catch_slackers` (line 280), after catching a slacker, if their status is `"chatting"`, end the conversation. Add after the timer cancel block (line 294):

```python
            # If chatting, end the conversation
            if worker.status == "chatting":
                for key, pair in list(self.friendships._chatting_pairs.items()):
                    if worker.id in pair:
                        other_id = pair[0] if pair[1] == worker.id else pair[1]
                        self.friendships.end_conversation(pair[0], pair[1])
                        self.office.remove_friend_group(pair[0], pair[1])
                        other = self.manager.get_worker(other_id)
                        if other and other.status == "chatting":
                            # Other friend also gets caught
                            other_widget = self.office._worker_widgets.get(other_id)
                            if other_widget:
                                other_widget.status_label.setText("\U0001f630 Sorry!")
                                other_widget.status_label.setStyleSheet(
                                    "color: #ff6b6b; font-size: 11px;"
                                )
                            QTimer.singleShot(
                                5000,
                                lambda oid=other_id: self._chef_send_to_work(oid, None),
                            )
                        break
```

- [ ] **Step 12: Clean up friendships when firing a worker**

In `_fire_worker` (around line 339), before `self.manager.remove_worker(worker_id)`, add:

```python
            self.friendships.remove_worker(worker_id)
```

- [ ] **Step 13: Verify the app launches**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.main import MainWindow; print('MainWindow imports OK')"`

Expected: `MainWindow imports OK`

- [ ] **Step 14: Commit**

```bash
git add src/main.py
git commit -m "feat: wire friendship tick, follow-friend, and conversation flow into MainWindow"
```

---

### Task 5: Create FriendGroupWidget

**Files:**
- Create: `src/friend_group_widget.py`

- [ ] **Step 1: Create `src/friend_group_widget.py`**

```python
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

        # Top row: Worker A ❤️ Worker B + level badge
        top_row = QHBoxLayout()

        # Worker A
        a_label = QLabel(f"{self.worker_a.emoji} {self.worker_a.name}")
        a_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")
        top_row.addWidget(a_label)

        # Heart
        heart = QLabel("❤️")
        heart.setStyleSheet("font-size: 16px;")
        top_row.addWidget(heart)

        # Worker B
        b_label = QLabel(f"{self.worker_b.emoji} {self.worker_b.name}")
        b_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px;")
        top_row.addWidget(b_label)

        top_row.addStretch()

        # Level badge
        level_badge = QLabel(f"Lv.{self.level}")
        level_badge.setStyleSheet(
            "background: #e91e63; color: white; padding: 2px 8px; "
            "border-radius: 4px; font-size: 10px; font-weight: bold;"
        )
        top_row.addWidget(level_badge)

        layout.addLayout(top_row)

        # Status row
        status = QLabel("● Chatting")
        status.setStyleSheet("color: #e91e63; font-size: 11px;")
        layout.addWidget(status)

        # Conversation snippet
        self.snippet_label = QLabel("")
        self.snippet_label.setStyleSheet(
            "color: #aaa; font-size: 11px; font-style: italic;"
        )
        self.snippet_label.setWordWrap(True)
        layout.addWidget(self.snippet_label)

        # Read conversation link
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
```

- [ ] **Step 2: Verify import**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.friend_group_widget import FriendGroupWidget; print('FriendGroupWidget imports OK')"`

Expected: `FriendGroupWidget imports OK`

- [ ] **Step 3: Commit**

```bash
git add src/friend_group_widget.py
git commit -m "feat: add FriendGroupWidget for grouped friend display in rooms"
```

---

### Task 6: Create FriendChatDialog

**Files:**
- Create: `src/friend_chat_dialog.py`

- [ ] **Step 1: Create `src/friend_chat_dialog.py`**

```python
from PyQt6.QtCore import Qt, QTimer
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

        # Header
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

        # Tabs
        tabs = QTabWidget()

        # Current conversation tab
        current_tab = self._build_conversation_widget(current_lines)
        tabs.addTab(current_tab, "Current")

        # History tab
        history_tab = self._build_history_widget(history)
        tabs.addTab(history_tab, f"History ({len(history)})")

        layout.addWidget(tabs)

        # Close button
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
            for conv in reversed(history):  # newest first
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
```

- [ ] **Step 2: Verify import**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.friend_chat_dialog import FriendChatDialog; print('FriendChatDialog imports OK')"`

Expected: `FriendChatDialog imports OK`

- [ ] **Step 3: Commit**

```bash
git add src/friend_chat_dialog.py
git commit -m "feat: add FriendChatDialog for viewing friend conversations"
```

---

### Task 7: Update OfficeView and WorkerWidget for friendship UI

**Files:**
- Modify: `src/office_view.py:1-9` (imports)
- Modify: `src/office_view.py:11-55` (RoomWidget)
- Modify: `src/office_view.py:57-184` (OfficeView)
- Modify: `src/worker_widget.py:31-112` (WorkerWidget)

- [ ] **Step 1: Add friend count indicator to WorkerWidget**

In `src/worker_widget.py`, add a `friend_label` in `_setup_ui`, after the salary label (after line 77):

```python
        # Friend count
        self.friend_label = QLabel("")
        self.friend_label.setStyleSheet("color: #e91e63; font-size: 9px;")
        layout.addWidget(self.friend_label)
```

Add a method to update it:

```python
    def update_friend_count(self, count: int):
        if count > 0:
            self.friend_label.setText(f"❤ {count} friend{'s' if count != 1 else ''}")
        else:
            self.friend_label.setText("")
```

- [ ] **Step 2: Add FriendGroupWidget support to RoomWidget**

In `src/office_view.py`, add import at top:

```python
from src.friend_group_widget import FriendGroupWidget
```

Add methods to `RoomWidget`:

```python
    def add_friend_group(self, widget: FriendGroupWidget):
        self._empty_label.hide()
        self._workers_layout.addWidget(widget)

    def remove_friend_group(self, widget: FriendGroupWidget):
        self._workers_layout.removeWidget(widget)
        widget.setParent(None)
        if not self._worker_widgets:
            self._empty_label.show()
```

- [ ] **Step 3: Add friendship methods to OfficeView**

Add import for `FriendChatDialog` at top of `src/office_view.py`:

```python
from src.friend_chat_dialog import FriendChatDialog
```

Add a signal and tracking dict to `OfficeView.__init__` (after line 63):

```python
        self._friend_groups: dict[str, FriendGroupWidget] = {}  # "id_a|id_b" -> widget
```

Add these methods to `OfficeView`:

```python
    def show_friend_group(self, worker_a: Worker, worker_b: Worker, level: int, room: str):
        """Replace individual worker widgets with a grouped friend card."""
        key = "|".join(sorted([worker_a.id, worker_b.id]))
        if key in self._friend_groups:
            return  # Already showing

        # Hide individual widgets
        w_a = self._worker_widgets.get(worker_a.id)
        w_b = self._worker_widgets.get(worker_b.id)
        if w_a:
            w_a.hide()
        if w_b:
            w_b.hide()

        # Create and add group widget
        group = FriendGroupWidget(worker_a, worker_b, level)
        group.clicked.connect(self._on_friend_group_clicked)
        self._friend_groups[key] = group

        target_room = self.rooms.get(room)
        if target_room:
            target_room.add_friend_group(group)

    def remove_friend_group(self, id_a: str, id_b: str):
        """Remove friend group widget and restore individual widgets."""
        key = "|".join(sorted([id_a, id_b]))
        group = self._friend_groups.pop(key, None)
        if not group:
            return

        # Remove from room
        for room in self.rooms.values():
            room.remove_friend_group(group)
        group.deleteLater()

        # Show individual widgets again
        w_a = self._worker_widgets.get(id_a)
        w_b = self._worker_widgets.get(id_b)
        if w_a:
            w_a.show()
        if w_b:
            w_b.show()

    def update_friend_group_conversation(self, id_a: str, id_b: str, lines: list[dict]):
        """Update the conversation snippet on a friend group widget."""
        key = "|".join(sorted([id_a, id_b]))
        group = self._friend_groups.get(key)
        if group:
            group.update_conversation(lines)

    def update_friend_indicator(self, worker_id: str, count: int):
        """Update the friend count indicator on a worker widget."""
        widget = self._worker_widgets.get(worker_id)
        if widget:
            widget.update_friend_count(count)

    def _on_friend_group_clicked(self, id_a: str, id_b: str):
        """Emit signal or open dialog when friend group is clicked."""
        self.worker_clicked.emit(f"friend:{id_a}:{id_b}")
```

- [ ] **Step 4: Commit**

```bash
git add src/worker_widget.py src/office_view.py
git commit -m "feat: add friendship UI to OfficeView and WorkerWidget"
```

---

### Task 8: Wire friend group display and dialog into MainWindow

**Files:**
- Modify: `src/main.py` (conversation display + dialog opening)

- [ ] **Step 1: Import FriendChatDialog**

In `src/main.py`, add import:

```python
from src.friend_chat_dialog import FriendChatDialog
```

- [ ] **Step 2: Show friend group widget when conversation starts**

In `_start_friend_conversation`, after setting both workers to chatting and before the AI call, add:

```python
        level = self.friendships.get_level(worker_a.id, worker_b.id)
        self.office.show_friend_group(worker_a, worker_b, level, room)
```

(Move the existing `level = ...` line up and reuse it.)

- [ ] **Step 3: Handle friend group click in `_open_chat`**

Modify `_open_chat` to detect friend group clicks. Replace the start of `_open_chat` (line 85):

```python
    def _open_chat(self, worker_id: str):
        # Check if this is a friend group click
        if worker_id.startswith("friend:"):
            parts = worker_id.split(":")
            if len(parts) == 3:
                self._open_friend_chat(parts[1], parts[2])
                return

        worker = self.manager.get_worker(worker_id)
        if not worker:
            return
        # ... rest of method unchanged
```

- [ ] **Step 4: Implement `_open_friend_chat`**

```python
    def _open_friend_chat(self, id_a: str, id_b: str):
        worker_a = self.manager.get_worker(id_a)
        worker_b = self.manager.get_worker(id_b)
        if not worker_a or not worker_b:
            return
        level = self.friendships.get_level(id_a, id_b)
        history = self.friendships.load_conversations(id_a, id_b)

        # Get current conversation lines from the group widget
        key = "|".join(sorted([id_a, id_b]))
        group = self.office._friend_groups.get(key)
        current_lines = group._conversation_lines if group else []

        dlg = FriendChatDialog(worker_a, worker_b, level, current_lines, history, self)
        dlg.exec()
```

- [ ] **Step 5: Verify the full app launches**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -c "from src.main import MainWindow; print('Full integration imports OK')"`

Expected: `Full integration imports OK`

- [ ] **Step 6: Commit**

```bash
git add src/main.py
git commit -m "feat: wire friend group display and conversation dialog into MainWindow"
```

---

### Task 9: End-to-end manual testing and polish

**Files:**
- Possibly touch any of the above files for bug fixes

- [ ] **Step 1: Launch the application**

Run: `cd /home/evgeniya/projects/moodMate-ai-assistant && python -m src.main`

- [ ] **Step 2: Test friendship formation**

1. Hire at least 2 workers with low salaries (< $200) so they procrastinate a lot
2. Assign them tasks and wait for them to go to kitchen/hallway
3. Verify that when 2 workers are in the same non-workspace room, friendship forms after ~10s
4. Check that the friend count indicator (❤ 1 friend) appears on worker cards

- [ ] **Step 3: Test follow-friend mechanic**

1. Wait for workers to become friends (Level 2+)
2. When one friend goes idle and the other procrastinates, watch if the idle one follows
3. Verify only idle workers with no pending tasks can follow

- [ ] **Step 4: Test conversation and group widget**

1. When two friends are in the same room, verify the FriendGroupWidget appears (pink border, hearts)
2. Click the group widget to open FriendChatDialog
3. Verify conversation lines appear (after AI generation completes)
4. Verify conversation history tab works

- [ ] **Step 5: Test Chef interaction with chatting workers**

1. Wait for two workers to start chatting
2. When Chef patrols into their room, verify both get "Sorry!" and get sent back to work
3. Verify the FriendGroupWidget disappears and individual widgets reappear

- [ ] **Step 6: Fix any bugs found during testing**

Apply minimal fixes. Don't over-engineer.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "fix: polish friendship system after manual testing"
```
