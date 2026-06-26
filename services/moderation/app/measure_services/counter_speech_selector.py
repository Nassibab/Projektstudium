class CounterSpeechSelector:
    """Entscheidet, ob eine Gegenrede erzeugt werden soll.

    Der alte Platzhalter gab immer False zurück. Dadurch wurde der Generator nie
    aufgerufen. Diese einfache Default-Logik aktiviert Gegenrede bei Warnstufen,
    hohem Score oder explizitem Test-/Debug-Flag im Kommentar.
    """

    def should_generate_counter_speech(self, comment, shitstorm_score, warning_level):
        if comment.get("force_counter_speech") is True:
            return True

        if str(warning_level).lower() in {"watch", "warning", "critical"}:
            return True

        try:
            return float(shitstorm_score) >= 20.0
        except (TypeError, ValueError):
            return False
