from openai import OpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class CounterSpeechGenerator:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("LLMAPI_KEY"),
            base_url="https://hub.nhr.fau.de/api/llmgw/v1",
        )

    def generate(
        self,
        comment: dict,
        thread_context: str = ""
    ) -> str:

        prompt = f"""
        You are a moderation assistant.

        Generate a constructive counter speech response.

        Requirements:
        - Remain polite and respectful.
        - De-escalate the discussion.
        - Do not insult anyone.
        - Encourage factual discussion.
        - Maximum 3 sentences.

        Thread context:
        {thread_context}

        Comment:
        {comment.get("text", "")}
        """

        response = self.client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
        )

        return response.choices[0].message.content