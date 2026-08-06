class CountermeasureService:
    """Minimaler Default, damit das Projekt auch ohne externes Measures-Modul läuft."""

    def decide_actions(self, shitstorm_score, warning_level="normal"):
        if warning_level == "critical":
            return {
                "level": warning_level,
                "actions": ["freeze_thread_review", "notify_moderation_team", "prioritize_human_review"],
            }
        if warning_level == "warning":
            return {
                "level": warning_level,
                "actions": ["notify_moderation_team", "increase_monitoring"],
            }
        if warning_level == "watch":
            return {
                "level": warning_level,
                "actions": ["increase_monitoring"],
            }
        return {"level": warning_level, "actions": []}
