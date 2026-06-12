import os

from openai import OpenAI

MODEL = "gpt-oss-120b"


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


llm_service = LLMService()
