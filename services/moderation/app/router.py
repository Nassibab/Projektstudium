from fastapi import APIRouter
from app.services.moderate import moderate

router = APIRouter()


@router.get("/")
def read_root():
    return {"message": "Moderation Service is running"}


@router.post("/moderate")
async def moderate_endpoint(payload: dict):
    return await moderate(payload)