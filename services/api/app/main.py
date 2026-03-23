from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time

app = FastAPI(title="Group Project API")

# Simple in-memory storage (for demo)
tasks = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.post("/tasks/")
async def create_task():
    task_id = len(tasks) + 1
    task = {"id": task_id, "status": "queued", "result": None}
    tasks.append(task)
    return {"task_id": task_id, "status": "queued"}

@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    for task in tasks:
        if task["id"] == task_id:
            return {"task_id": task_id, "status": task["status"]}
    return {"task_id": task_id, "status": "unknown"}
