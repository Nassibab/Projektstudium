import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="Group Project API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
