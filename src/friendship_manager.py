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
