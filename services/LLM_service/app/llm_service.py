import json
import os

from openai import OpenAI
from pydantic import ValidationError

from .prompts.comment_analysis import COMMENT_ANALYSIS_SYSTEM_MESSAGE
from .schemas.comment_analysis import (
    CommentAnalysisResult,
    CommentScores,
    LLMRawOutput,
    ThreadAnalysisRequest,
    ThreadAnalysisResponse,
)

MODEL = "gpt-oss-120b"

# Above this many comments in one thread, split into chunks to stay within
# the model's context/output limits. Still far fewer calls than one-per-comment.
MAX_COMMENTS_PER_CALL = 50

IRONY_SYSTEM_MESSAGE = (
    "You analyze social media comments for irony and sarcasm. "
    "Explain whether the text is ironic, why or why not, and how confident you are."
)
COUNTERMEASURES_SYSTEM_MESSAGE = (
    "You suggest practical countermeasures for de-escalating online shitstorms. "
    "Provide clear, actionable recommendations tailored to the given context."
)


class LLMService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=os.environ["NHR_LLM_BASE_URL"],
                api_key=os.environ["NHR_LLM_API_KEY"],
            )
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty content")
        return content

    def analyze_irony(self, text: str, temperature: float = 0.7) -> str:
        return self.chat(
            messages=[
                {"role": "system", "content": IRONY_SYSTEM_MESSAGE},
                {"role": "user", "content": text},
            ],
            temperature=temperature,
        )

    def suggest_countermeasures(self, context: str, temperature: float = 0.7) -> str:
        return self.chat(
            messages=[
                {"role": "system", "content": COUNTERMEASURES_SYSTEM_MESSAGE},
                {"role": "user", "content": context},
            ],
            temperature=temperature,
        )

    def analyze_thread_comments(
        self, request: ThreadAnalysisRequest
    ) -> ThreadAnalysisResponse:
        results: list[CommentAnalysisResult] = []

        comments = _dedupe_comments(request.comments)
        for start in range(0, len(comments), MAX_COMMENTS_PER_CALL):
            chunk = comments[start : start + MAX_COMMENTS_PER_CALL]
            results.extend(
                self._analyze_chunk(
                    thread_id=request.thread_id,
                    chunk=chunk,
                    temperature=request.temperature,
                )
            )

        return ThreadAnalysisResponse(thread_id=request.thread_id, results=results)

    def _analyze_chunk(self, thread_id, chunk, temperature) -> list[CommentAnalysisResult]:
        expected_ids = {str(c.comment_id) for c in chunk}

        user_payload = json.dumps(
            {
                "thread_id": thread_id,
                "comments": [
                    {"comment_id": str(c.comment_id), "text": c.text} for c in chunk
                ],
            },
            ensure_ascii=False,
        )

        messages = [
            {"role": "system", "content": COMMENT_ANALYSIS_SYSTEM_MESSAGE},
            {"role": "user", "content": user_payload},
        ]

        last_error: Exception | None = None
        for attempt in range(2):
            raw = None
            try:
                raw = self._complete_json(messages, temperature)
                payload = _normalize_llm_payload(_extract_json_object(raw))
                parsed = LLMRawOutput.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                snippet = (raw[:300] + "...") if raw else "<no content>"
                last_error = ValueError(f"{exc} | raw={snippet!r}")
                continue

            returned_ids = [str(item.comment_id) for item in parsed.results]

            if set(returned_ids) != expected_ids or len(returned_ids) != len(expected_ids):
                last_error = ValueError(
                    f"LLM comment_ids {sorted(set(returned_ids))} do not match "
                    f"input {sorted(expected_ids)}"
                )
                continue

            return [
                CommentAnalysisResult(
                    comment_id=str(item.comment_id),
                    scores=CommentScores(
                        **item.model_dump(exclude={"comment_id"})
                    ),
                )
                for item in parsed.results
            ]

        raise ValueError(f"LLM analysis failed after retry: {last_error}")

    def _complete_json(self, messages, temperature) -> str:
        try:
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Gateway may not support response_format; fall back to plain mode.
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=temperature,
            )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty content")
        return _strip_json_fences(content)


def _dedupe_comments(comments):
    seen: set[str] = set()
    unique = []
    for comment in comments:
        cid = str(comment.comment_id)
        if cid not in seen:
            seen.add(cid)
            unique.append(comment)
    return unique


_LLM_SCORE_DEFAULTS: dict[str, int] = {
    "irony": 1,
    "attack_score": 1,
    "toxicity_score": 1,
    "swearword_count": 0,
    "negative_word_count": 0,
    "insult_count": 0,
    "direct_address_count": 0,
    "imperative_count": 0,
    "accusation_marker_count": 0,
    "mockery_marker_count": 0,
    "is_attacking": 0,
}


def _normalize_llm_payload(data: dict) -> dict:
    """Fill missing score keys the LLM sometimes omits before strict validation."""
    results = data.get("results")
    if not isinstance(results, list):
        return data

    normalized: list[dict] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        for key, default in _LLM_SCORE_DEFAULTS.items():
            if key not in row or row[key] is None:
                row[key] = default
        normalized.append(row)

    return {"results": normalized}


def _extract_json_object(raw: str) -> dict:
    """Parse the LLM JSON, tolerating leading/trailing junk some gateways emit.

    Some deployments prepend a stray ``{"`` artifact before the real
    ``{"results": [...]}`` object. We first try a strict parse, then fall back
    to locating the ``"results"`` object and decoding from its opening brace.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    key_idx = raw.find('"results"')
    if key_idx != -1:
        brace_idx = raw.rfind("{", 0, key_idx)
        if brace_idx != -1:
            obj, _ = json.JSONDecoder().raw_decode(raw[brace_idx:])
            return obj

    raise json.JSONDecodeError("No decodable JSON object found", raw, 0)


def _strip_json_fences(content: str) -> str:
    text = content.strip()
    # Some gateways prepend a stray `{"` before the real JSON object.
    while text.startswith('{"{"'):
        text = text[2:]
    if not text.startswith("```"):
        return text
    # Drop the opening fence line (e.g. ``` or ```json) and any closing fence.
    text = text[3:]
    text = text.removeprefix("json")
    if "```" in text:
        text = text[: text.rfind("```")]
    return text.strip()


llm_service = LLMService()
