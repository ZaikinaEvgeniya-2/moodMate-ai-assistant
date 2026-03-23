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
