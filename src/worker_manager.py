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
