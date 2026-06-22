class CountermeasureService:
    def decide_actions(self, shitstorm_score: float, warning_level: str) -> dict:
        actions = []

        if warning_level == "normal":
            actions.append({
                "type": "none",
                "message": "No countermeasure required."
            })

        elif warning_level == "watch":
            actions.extend([
                {
                    "type": "monitor_thread",
                    "message": "Increase monitoring for this thread."
                },
                {
                    "type": "log_event",
                    "message": "Store warning event for later analysis."
                }
            ])

        elif warning_level == "warning":
            actions.extend([
                {
                    "type": "notify_moderator",
                    "message": "Notify a moderator about increased escalation risk."
                },
                {
                    "type": "highlight_thread",
                    "message": "Mark the thread as potentially escalating."
                },
                {
                    "type": "increase_analysis_frequency",
                    "message": "Analyze incoming comments more frequently."
                }
            ])

        elif warning_level == "critical":
            actions.extend([
                {
                    "type": "urgent_moderator_alert",
                    "message": "Send urgent alert to moderation team."
                },
                {
                    "type": "temporary_slow_mode",
                    "message": "Suggest temporary slow mode for the thread."
                },
                {
                    "type": "prioritize_review",
                    "message": "Prioritize this thread in the moderation dashboard."
                },
                {
                    "type": "prepare_public_response",
                    "message": "Suggest preparing an official response or clarification."
                }
            ])

        return {
            "shitstorm_score": shitstorm_score,
            "warning_level": warning_level,
            "recommended_actions": actions
        }