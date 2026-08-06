"""Rückwärtskompatibler Importpfad für den neuen Counter-Speech-Generator.

Alte Module importieren weiterhin `app.measure_services.counter_speech_generator`.
Damit diese Stellen nicht brechen, wird hier bewusst die neue Implementierung
weitergereicht.
"""

from app.measure_services.counter_speech_generator_extended import (  # noqa: F401
    CounterSpeechGenerator,
    DEFAULT_MODEL_NAME,
    DEFAULT_PROMPT_TEMPLATE,
)
