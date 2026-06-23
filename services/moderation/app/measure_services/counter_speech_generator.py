import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class CounterSpeechGenerator:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("LLMAPI_KEY"),
            base_url="https://hub.nhr.fau.de/api/llmgw/v1",
        )

        # Standardmodell
        self.model = "gpt-oss-120b"

        # Fester Produktiv-Prompt
        self.prompt_template = """
Du bist Moderationsassistent. Erstelle eine konstruktive Gegenrede, um die gesamte Diskussion zu deeskalieren.

Dir wird der Ausgangskommentar (root bzw. Parent) und der darauffolgende Diskussionsverlauf übergeben.

Führe vor der Antwort intern folgende Analyse durch:
1. Analysiere die Dynamik und das Eskalationspotenzial.
2. Entwirf intern mehrere deeskalierende Strategien.
3. Wähle die psychologisch wirksamste Strategie.

Anforderungen:
- Höflich und respektvoll.
- Deeskalierend.
- Maximal 3 Sätze.
- Keine Fragen stellen.
- Keine Einleitung.
- Gib ausschließlich die endgültige Antwort aus.

CONTEXT:
{thread_context}

DISKUSSIONSVERLAUF:
{discussion_history}
"""

    def generate(
        self,
        thread_context: str,
        discussion_history: str
    ) -> str:

        prompt = self.prompt_template.format(
            thread_context=thread_context,
            discussion_history=discussion_history
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )

        return response.choices[0].message.content.strip()