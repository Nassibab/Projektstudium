from fastapi import APIRouter

from .data import create_task, get_task, get_websites

from app.services.mongodb_graph_sync import sync_all_threads_to_graph

from app.services.report_service import get_thread_report

from app.importers.professor_json_importer import import_json


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

@router.post("/import/professor")
def import_professor_data_into_MongoDB():
    import_json()

    return {
        "status": "success",
        "message": "Professor data imported"
    }

@router.post("/sync/graph")
def sync_MongoDB_NEO4J():
    return sync_all_threads_to_graph()

@router.get("/report/threads")
def report_threads_in_MongoDB_and_NEO4J():
    return get_thread_report()
