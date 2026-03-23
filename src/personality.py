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
        elif status == "chatting":
            return (status, 0)
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
