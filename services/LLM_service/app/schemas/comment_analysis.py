from typing import Literal

from pydantic import BaseModel, Field


class CommentInput(BaseModel):
    comment_id: str | int
    text: str = Field(..., min_length=1)


class ThreadAnalysisRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    comments: list[CommentInput] = Field(..., min_length=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class CommentScores(BaseModel):
    irony: int = Field(..., ge=1, le=5)
    attack_score: int = Field(..., ge=1, le=10)
    toxicity_score: int = Field(..., ge=1, le=4)
    swearword_count: int = Field(..., ge=0)
    negative_word_count: int = Field(..., ge=0)
    insult_count: int = Field(..., ge=0)
    direct_address_count: int = Field(..., ge=0)
    imperative_count: int = Field(..., ge=0)
    accusation_marker_count: int = Field(..., ge=0)
    mockery_marker_count: int = Field(..., ge=0)
    is_attacking: Literal[0, 1]


class CommentAnalysisResult(BaseModel):
    comment_id: str | int
    scores: CommentScores


class ThreadAnalysisResponse(BaseModel):
    thread_id: str
    results: list[CommentAnalysisResult]


class LLMRawCommentScore(CommentScores):
    """Exact per-comment shape the LLM is asked to emit: comment_id + flat scores."""

    comment_id: str | int


class LLMRawOutput(BaseModel):
    results: list[LLMRawCommentScore]
