REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
MODELS_URL = "/api/v1/ml/models"
CATEGORIZE_URL = "/api/v1/ml/categorize"


def _auth_headers(client, email="mluser@example.com"):
    client.post(REGISTER_URL, json={"email": email, "password": "supersecret1", "full_name": "ML Tester"})
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_model_status_requires_auth(client):
    response = client.get(MODELS_URL)
    assert response.status_code == 401


def test_model_status_returns_registry_info(client):
    headers = _auth_headers(client)
    response = client.get(MODELS_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    # transaction-classifier (Phase 4), anomaly-detector (Phase 5),
    # expense-forecaster (Phase 7).
    assert len(body) == 3
    model_names = {entry["model_name"] for entry in body}
    assert model_names == {"transaction-classifier", "anomaly-detector", "expense-forecaster"}
    for entry in body:
        assert isinstance(entry["is_ready"], bool)


def test_categorize_requires_auth(client):
    response = client.post(CATEGORIZE_URL, json={"description": "SWIGGY ORDER"})
    assert response.status_code == 401


def test_categorize_returns_valid_schema(client):
    headers = _auth_headers(client)
    response = client.post(CATEGORIZE_URL, headers=headers, json={"description": "SWIGGY ORDER"})
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["category"], str)
    assert 0.0 <= body["confidence"] <= 1.0


def test_categorize_rejects_empty_description(client):
    headers = _auth_headers(client)
    response = client.post(CATEGORIZE_URL, headers=headers, json={"description": ""})
    assert response.status_code == 422
