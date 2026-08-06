from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL_NAME = os.getenv("COUNTER_SPEECH_MODEL", "gpt-oss-120b")
DEFAULT_LLM_BASE_URL = os.getenv(
    "LLMAPI_BASE_URL",
    "https://hub.nhr.fau.de/api/llmgw/v1",
)
DEFAULT_MAX_CONTEXT_COMMENTS = int(os.getenv("COUNTER_SPEECH_MAX_CONTEXT_COMMENTS", "20"))

DEFAULT_PROMPT_TEMPLATE = """
*Rolle*
Du bist ein Moderationsassistent zur Unterstützung der Erkennung und Deeskalation von Shitstorms.
Deine Aufgabe besteht darin, auf Grundlage eines Diskussionsverlaufs eine deeskalierende Gegenrede zu generieren.

*Denke Schritt für Schritt nach, gib diese Analyse aber nicht aus.*
1. Analysiere die Dynamik und den Kontext der Diskussion.
2. Erkenne die Emotionen und mögliche Eskalationspunkte.
3. Bewerte den Eskalationsgrad.
4. Entwerfe mehrere deeskalierende Antwortstrategien.
5. Wähle die geeignetste Strategie hinsichtlich Empathie, Neutralität, Sachlichkeit und Deeskalationspotenzial.
6. Generiere die finale Gegenrede.

*Anforderungen*
- Gib NUR die finale Gegenrede aus.
- Maximal 4 Sätze.
- Neutral und nicht belehrend.
- Keine Partei bevorzugen.
- Empathisch und erklärend, wenn es zur Situation passt.
- Sachliche Diskussion fördern.
- Natürlicher Sprachstil.
- Keine standardisierten Floskeln, Dankesformeln oder generischen Formulierungen.

CONTEXT (Ausgangskommentar oder Thread-Kontext):
{thread_context}

DISKUSSIONSVERLAUF:
{comment_text}
""".strip()


class CounterSpeechGenerator:
    """Generiert deeskalierende Gegenrede mit dem neuen Prompt-basierten Generator.

    Die Klasse ist bewusst service-tauglich:
    - Standardmodell und Prompt liegen in der Klasse/Konfiguration.
    - Der OpenAI-Client wird erst beim tatsächlichen Generieren erstellt.
    - `generate_for_comment` baut aus Kommentar + vorherigen Kommentaren automatisch
      den Diskussionsverlauf für den neuen Generator.
    """

    def __init__(
        self,
        model_name: str | None = None,
        prompt_template: str | None = None,
        temperature: float = 0.7,
        max_context_comments: int = DEFAULT_MAX_CONTEXT_COMMENTS,
    ):
        self.model_name = model_name or DEFAULT_MODEL_NAME
        self.prompt_template = prompt_template or DEFAULT_PROMPT_TEMPLATE
        self.temperature = temperature
        self.max_context_comments = max_context_comments
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = os.getenv("LLMAPI_KEY")
            if not api_key:
                raise RuntimeError(
                    "LLMAPI_KEY ist nicht gesetzt. Ohne API-Key kann keine Gegenrede generiert werden."
                )

            # Import erst hier, damit der Moderation-Service auch ohne installierte
            # OpenAI-Bibliothek starten kann, solange keine Gegenrede erzeugt wird.
            from openai import OpenAI

            self._client = OpenAI(
                api_key=api_key,
                base_url=DEFAULT_LLM_BASE_URL,
            )
        return self._client

    def generate(
        self,
        model_name: str | None = None,
        prompt_template: str | None = None,
        thread_context: str = "",
        diskussions_verlauf: str = "",
    ) -> str:
        """Direkter Aufruf des neuen Generators mit expliziten Promptdaten."""
        prompt = (prompt_template or self.prompt_template).format(
            thread_context=thread_context or "Kein zusätzlicher Thread-Kontext vorhanden.",
            comment_text=diskussions_verlauf or "Kein Diskussionsverlauf vorhanden.",
        )

        response = self._get_client().chat.completions.create(
            model=model_name or self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )

        return (response.choices[0].message.content or "").strip()

    def generate_for_comment(
        self,
        comment: dict[str, Any],
        previous_comments: list[dict[str, Any]] | None = None,
        thread_context: str | None = None,
    ) -> str:
        """Service-Aufruf: baut Kontext aus aktuellem Kommentar und Verlauf."""
        resolved_context = (
            thread_context
            if thread_context is not None
            else self._resolve_thread_context(comment, previous_comments)
        )
        discussion_text = self.build_discussion_text(comment, previous_comments)

        return self.generate(
            model_name=comment.get("counter_speech_model") or self.model_name,
            prompt_template=comment.get("counter_speech_prompt_template") or self.prompt_template,
            thread_context=resolved_context,
            diskussions_verlauf=discussion_text,
        )

    def build_discussion_text(
        self,
        comment: dict[str, Any],
        previous_comments: list[dict[str, Any]] | None = None,
    ) -> str:
        """Erstellt den Diskussionsverlauf für den Prompt.

        Unterstützt beide Eingabeformen:
        - `comment["diskussions_verlauf"]` / `comment["discussion_history"]`
        - `previous_comments` aus dem Live-Payload plus aktueller Kommentar
        """
        explicit_history = (
            comment.get("diskussions_verlauf")
            or comment.get("discussion_history")
            or comment.get("comment_text")
        )
        if explicit_history:
            return str(explicit_history).strip()

        if previous_comments is None:
            previous_comments = comment.get("previous_comments") or []

        relevant_previous = list(previous_comments)[-self.max_context_comments :]
        lines: list[str] = []

        for previous in relevant_previous:
            text = str(previous.get("text", "")).strip()
            if not text:
                continue
            login = str(previous.get("login", "Nutzer")).strip() or "Nutzer"
            lines.append(f"- {login}: {text}")

        current_text = str(comment.get("text", "")).strip()
        if current_text:
            current_login = str(comment.get("login", "Aktueller Kommentar")).strip() or "Aktueller Kommentar"
            lines.append(f"- {current_login}: {current_text}")

        return "\n".join(lines)

    @staticmethod
    def _resolve_thread_context(
        comment: dict[str, Any],
        previous_comments: list[dict[str, Any]] | None = None,
    ) -> str:
        for key in (
            "thread_context",
            "parent_text",
            "root_text",
            "thread_title",
            "subject",
        ):
            value = comment.get(key)
            if value:
                return str(value).strip()

        thread = comment.get("thread")
        if isinstance(thread, dict):
            for key in ("text", "title", "subject"):
                value = thread.get(key)
                if value:
                    return str(value).strip()

        # Fallback: frühester bekannter Kommentar als grober Ausgangskontext.
        if previous_comments:
            first_text = str(previous_comments[0].get("text", "")).strip()
            if first_text:
                return first_text

        return ""
