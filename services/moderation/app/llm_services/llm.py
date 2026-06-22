from openai import OpenAI
import os



client = OpenAI(
    api_key=os.getenv("LLMAPI_KEY"),
    base_url="https://hub.nhr.fau.de/api/llmgw/v1",
)

def test_llm() -> str:
    response = client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": "Sag Hallo."
            }
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content 

