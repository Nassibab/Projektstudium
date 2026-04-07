from fastapi import APIRouter

from .data import create_task, get_task, get_websites

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "API is running"}


@router.post("/tasks/")
async def create_task_endpoint():
    return create_task()


@router.get("/tasks/{task_id}")
def get_task_endpoint(task_id: int):
    return get_task(task_id)


@router.get("/websites")
def get_websites_endpoint():
    return get_websites()
