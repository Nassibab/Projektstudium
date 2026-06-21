from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router
from app.services.demo_cache import ensure_cached_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ensure_cached_demo_data(force_refresh=True)
    except Exception as exc:
        print(f"Warning: Could not initialize demo cache at startup: {exc}")
    yield

app = FastAPI(title="Group Project API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)