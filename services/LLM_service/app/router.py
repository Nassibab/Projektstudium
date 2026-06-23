from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .limiter import get_rate_limit, limiter
from .llm_service import llm_service
from .schemas.comment_analysis import ThreadAnalysisRequest, ThreadAnalysisResponse

router = APIRouter()
_rate_limit = get_rate_limit()


class ChatRequest(BaseModel):
    user_message: str = Field(..., min_length=1)
    system_message: str = "You are a helpful assistant."
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    content: str


class IronyRequest(BaseModel):
    text: str = Field(..., min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class CountermeasuresRequest(BaseModel):
    context: str = Field(..., min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


@router.get("/")
def read_root() -> dict[str, str]:
    return {"message": "LLM Service is running"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-service"}


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(_rate_limit)
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    content = llm_service.chat(
        messages=[
            {"role": "system", "content": body.system_message},
            {"role": "user", "content": body.user_message},
        ],
        temperature=body.temperature,
    )
    return ChatResponse(content=content)


@router.post("/irony", response_model=ChatResponse)
@limiter.limit(_rate_limit)
def irony(request: Request, body: IronyRequest) -> ChatResponse:
    content = llm_service.analyze_irony(
        text=body.text,
        temperature=body.temperature,
    )
    return ChatResponse(content=content)


@router.post("/countermeasures", response_model=ChatResponse)
@limiter.limit(_rate_limit)
def countermeasures(request: Request, body: CountermeasuresRequest) -> ChatResponse:
    content = llm_service.suggest_countermeasures(
        context=body.context,
        temperature=body.temperature,
    )
    return ChatResponse(content=content)


@router.post("/analyze/thread", response_model=ThreadAnalysisResponse)
@limiter.limit(_rate_limit)
def analyze_thread(request: Request, body: ThreadAnalysisRequest) -> ThreadAnalysisResponse:
    try:
        return llm_service.analyze_thread_comments(body)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
