from __future__ import annotations

import os
import traceback

import requests
from fastapi import HTTPException

from app.evaluate_thread_payload import evaluate_thread_payload


API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")


def evaluate_thread_from_api(
    thread_id: str,
    platform: str,
    source_file: str | None = None,
    window_minutes: int = 5,
    rolling_window_size: int = 5,
    min_history: int = 3,
    z_watch: float = 1.0,
    z_full: float = 3.0,
    cusum_reference: float = 0.5,
    cusum_watch: float = 1.5,
    cusum_full: float = 5.0,
    watch_threshold: float = 0.20,
    warning_threshold: float = 0.40,
    critical_threshold: float = 0.60,
):
    try:
        params = {"platform": platform}

        if source_file is not None:
            params["source_file"] = source_file

        response = requests.get(
            f"{API_BASE_URL}/moderation/thread/{thread_id}",
            params=params,
            timeout=60,
        )

        response.raise_for_status()

        thread_json = response.json()

        evaluation_result = evaluate_thread_payload(
            thread_data=thread_json,
            output_dir="evaluation_results",
            run_name=f"{platform}_{thread_id}",
            window_minutes=window_minutes,
            rolling_window_size=rolling_window_size,
            min_history=min_history,
            z_watch=z_watch,
            z_full=z_full,
            cusum_reference=cusum_reference,
            cusum_watch=cusum_watch,
            cusum_full=cusum_full,
            watch_threshold=watch_threshold,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )

        return {
            "status": "success",
            "message": "Thread wurde abgerufen und mit Rolling-z/CUSUM, Aggressions-Cap und konfigurierbaren Warnschwellen evaluiert.",
            "thread_id": thread_id,
            "platform": platform,
            "scoring_config": evaluation_result["scoring_config"],
            "summary": evaluation_result["summary"],
            "rows": evaluation_result["rows"],
            "windows": evaluation_result["windows"],
            "files": evaluation_result["files"],
        }

    except requests.HTTPError as exc:
        api_response = exc.response

        raise HTTPException(
            status_code=api_response.status_code if api_response is not None else 502,
            detail={
                "message": "API-Container hat einen Fehler zurückgegeben.",
                "api_status_code": api_response.status_code if api_response is not None else None,
                "api_response": api_response.text if api_response is not None else str(exc),
            },
        ) from exc

    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "API-Container konnte nicht erreicht werden.",
                "api_base_url": API_BASE_URL,
                "error": str(exc),
            },
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": str(exc),
                "trace": traceback.format_exc(),
            },
        ) from exc
