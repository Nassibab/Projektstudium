from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from .router import router


def _load_project_env() -> None:
    for parent in Path(__file__).resolve().parents:
        env_file = parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            return


_load_project_env()

app = FastAPI(title="LLM Service")
app.include_router(router)
