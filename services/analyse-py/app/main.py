from fastapi import FastAPI
from .router import router

app = FastAPI(title="Analyse-py Service")

app.include_router(router)