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
        )

        return {
            "status": "success",
            "message": "Thread wurde abgerufen und mit dem neuen Standardvariablen-Format evaluiert.",
            "thread_id": thread_id,
            "platform": platform,
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

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": str(exc),
                "trace": traceback.format_exc(),
            },
        ) from exc
