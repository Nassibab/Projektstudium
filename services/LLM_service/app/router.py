from fastapi import APIRouter
from pydantic import BaseModel, Field

from .llm_service import llm_service

router = APIRouter()


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1)
    system_message: str = "You are a helpful assistant."
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    content: str


@router.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LLM Service is running"}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    content = llm_service.chat(
        messages=[
            {"role": "system", "content": request.system_message},
            {"role": "user", "content": request.user_message},
        ],
        temperature=request.temperature,
    )
    return ChatResponse(content=content)
