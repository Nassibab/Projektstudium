import os
import requests

from app.services.llm_analysis_service import (
    analyze_one_bluesky_comment_with_llm_service,
)

ANALYSE_R_URL = os.getenv("ANALYSE_R_URL", "http://analyse-r:8000")


def run_bluesky_comment_pipeline(thread_id: str, comment_id: str) -> dict:
    llm_result = analyze_one_bluesky_comment_with_llm_service(
        thread_id=thread_id,
        comment_id=comment_id,
    )

    predict_response = requests.get(
        f"{ANALYSE_R_URL}/predict-bluesky",
        timeout=1200,
    )
    predict_response.raise_for_status()

    return {
        "status": "success",
        "thread_id": thread_id,
        "comment_id": comment_id,
        "llm_result": llm_result,
        "prediction_status_code": predict_response.status_code,
    }