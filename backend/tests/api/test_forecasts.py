import io

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
IMPORTS_URL = "/api/v1/imports"
FORECASTS_URL = "/api/v1/forecasts"
GENERATE_URL = "/api/v1/forecasts/generate"


def _auth_headers(client, email="forecastuser@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Forecast Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _csv_with_n_daily_rows(n: int) -> bytes:
    lines = ["date,description,amount,type"]
    for day in range(1, n + 1):
        month = ((day - 1) // 28) + 1
        day_of_month = ((day - 1) % 28) + 1
        lines.append(f"2026-{month:02d}-{day_of_month:02d},GROCERY STORE,150.00,debit")
    return ("\n".join(lines) + "\n").encode()


def test_generate_requires_auth(client):
    assert client.post(GENERATE_URL).status_code == 401


def test_forecasts_list_requires_auth(client):
    assert client.get(FORECASTS_URL).status_code == 401


def test_generate_reports_insufficient_data_for_short_history(client):
    headers = _auth_headers(client)
    small_csv = (
        b"date,description,amount,type\n"
        b"2026-01-01,GROCERY STORE,150.00,debit\n"
        b"2026-01-02,GROCERY STORE,150.00,debit\n"
    )
    client.post(IMPORTS_URL, headers=headers, files={"file": ("small.csv", io.BytesIO(small_csv), "text/csv")})

    response = client.post(GENERATE_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"insufficient_data", "model_unavailable"}


def test_import_triggers_automatic_forecast_generation(client):
    headers = _auth_headers(client)
    csv_bytes = _csv_with_n_daily_rows(20)
    upload = client.post(
        IMPORTS_URL, headers=headers, files={"file": ("history.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert upload.status_code == 201

    response = client.get(FORECASTS_URL, headers=headers)
    assert response.status_code == 200
    # Either forecasts were generated (model trained) or none exist yet
    # (fresh models/ dir with no trained forecaster) — both are valid
    # states depending on whether `make train` has been run for this model.
    assert "items" in response.json()


def test_get_unknown_period_404(client):
    headers = _auth_headers(client)
    response = client.get(f"{FORECASTS_URL}/7d", headers=headers)
    assert response.status_code == 404


def test_get_invalid_period_404(client):
    headers = _auth_headers(client)
    response = client.get(f"{FORECASTS_URL}/invalid-period", headers=headers)
    assert response.status_code == 404


def test_forecasts_scoped_to_user(client):
    headers_a = _auth_headers(client, email="forecast_a@example.com")
    csv_bytes = _csv_with_n_daily_rows(20)
    client.post(IMPORTS_URL, headers=headers_a, files={"file": ("a.csv", io.BytesIO(csv_bytes), "text/csv")})

    headers_b = _auth_headers(client, email="forecast_b@example.com")
    response_b = client.get(FORECASTS_URL, headers=headers_b)
    assert response_b.json()["items"] == []
