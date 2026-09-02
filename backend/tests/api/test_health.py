HEALTH_URL = "/health"
READY_URL = "/ready"


def test_health_returns_healthy(client):
    response = client.get(HEALTH_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["mongodb"] == "connected"


def test_ready_reports_db_and_model_status(client):
    response = client.get(READY_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["mongodb"] is True
    assert set(body["models"].keys()) == {
        "transaction-classifier",
        "anomaly-detector",
        "expense-forecaster",
    }
    for is_ready in body["models"].values():
        assert isinstance(is_ready, bool)
