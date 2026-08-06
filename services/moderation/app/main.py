from fastapi import FastAPI

from app.router import router

app = FastAPI(title="Shitstorm Moderation Service", version="2.0.0")
app.include_router(router)
