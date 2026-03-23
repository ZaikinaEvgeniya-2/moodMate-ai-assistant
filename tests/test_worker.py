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
