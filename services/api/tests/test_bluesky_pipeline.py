import requests

from app.services import bluesky_pipeline_service
from app.database_services import mongo_data_service


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, *args, **kwargs):
        return list(self._docs)


# 1. Happy path: LLM runs, then R prediction succeeds.
def test_run_bluesky_analysis_happy_path(monkeypatch):
    calls = {"llm": 0, "get": 0}

    def fake_llm():
        calls["llm"] += 1
        return {"status": "success", "comments_processed": 3, "inserted_count": 3}

    def fake_get(url, timeout=None):
        calls["get"] += 1
        return _FakeResponse({"status": "success", "predicted_rows": 3, "save_status": {}})

    monkeypatch.setattr(
        bluesky_pipeline_service, "analyze_bluesky_with_llm_service", fake_llm
    )
    monkeypatch.setattr(bluesky_pipeline_service.requests, "get", fake_get)

    result = bluesky_pipeline_service.run_bluesky_analysis()

    assert calls == {"llm": 1, "get": 1}
    assert result["status"] == "success"
    assert result["llm"]["comments_processed"] == 3
    assert result["predict"]["predicted_rows"] == 3


# 2. R fails: should return a clean error naming the predict step, not crash.
def test_run_bluesky_analysis_when_r_fails(monkeypatch):
    def fake_llm():
        return {"status": "success", "comments_processed": 1, "inserted_count": 1}

    def fake_get(url, timeout=None):
        raise requests.RequestException("analyse-r unreachable")

    monkeypatch.setattr(
        bluesky_pipeline_service, "analyze_bluesky_with_llm_service", fake_llm
    )
    monkeypatch.setattr(bluesky_pipeline_service.requests, "get", fake_get)

    result = bluesky_pipeline_service.run_bluesky_analysis()

    assert result["status"] == "error"
    assert result["step"] == "predict"
    assert "analyse-r unreachable" in result["message"]


# 3. Read endpoint returns the expected shape.
def test_get_bluesky_analysis_results_shape(monkeypatch):
    fake_data = {
        "bluesky_prediction_comments_results": [{"comment_id": "c1"}],
        "bluesky_prediction_thread_results": [{"thread_id": "t1"}],
        "bluesky_prediction_user_results": [{"login": "u1"}],
    }

    def fake_collection(name):
        return _FakeCollection(fake_data.get(name, []))

    monkeypatch.setattr(mongo_data_service.mongo, "collection", fake_collection)

    result = mongo_data_service.get_bluesky_analysis_results()

    assert set(result.keys()) == {"comments", "threads", "users"}
    assert result["comments"] == [{"comment_id": "c1"}]
    assert result["threads"] == [{"thread_id": "t1"}]
    assert result["users"] == [{"login": "u1"}]
