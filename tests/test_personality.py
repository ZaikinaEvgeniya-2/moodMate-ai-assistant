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
    assert "working" in results


def test_kitchen_timer_returns():
    engine = BehaviorEngine()
    w = make_worker(50, "in_kitchen")
    new_status, delay = engine.decide_next_status(w)
    assert new_status in ("wandering", "working", "idle")
