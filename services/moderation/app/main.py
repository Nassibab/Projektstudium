from fastapi import FastAPI
from .router import router

app = FastAPI(title="Moderation Service")

app.include_router(router)