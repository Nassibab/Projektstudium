from typing import Dict, List

# Simple in-memory storage (for demo)
tasks: List[Dict] = []

websites = [
    {"id": 1, "name": "News 1", "value": 2},
    {"id": 2, "name": "News 2", "value": 4},
    {"id": 3, "name": "News 3", "value": 1},
    {"id": 4, "name": "News 4", "value": 6},
]


def create_task() -> Dict:
    task_id = len(tasks) + 1
    task = {"id": task_id, "status": "queued", "result": None}
    tasks.append(task)
    return {"task_id": task_id, "status": "queued"}


def get_task(task_id: int) -> Dict:
    for task in tasks:
        if task["id"] == task_id:
            return {"task_id": task_id, "status": task["status"]}
    return {"task_id": task_id, "status": "unknown"}


def get_websites() -> List[Dict]:
    return websites
