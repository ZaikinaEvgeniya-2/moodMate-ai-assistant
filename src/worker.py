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
            "working_dir": self.working_dir,
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
            working_dir=data.get("working_dir", ""),
        )
