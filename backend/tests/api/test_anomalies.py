import io

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
IMPORTS_URL = "/api/v1/imports"
TRANSACTIONS_URL = "/api/v1/transactions"
ANOMALIES_URL = "/api/v1/anomalies"
DETECT_URL = "/api/v1/anomalies/detect"


def _auth_headers(client, email="anomalyuser@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Anomaly Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _csv_with_n_normal_rows_plus_spike(n: int) -> bytes:
    lines = ["date,description,amount,type"]
    for i in range(n):
        day = (i % 27) + 1
        lines.append(f"2026-01-{day:02d},SWIGGY ORDER,{400 + (i % 5) * 10}.00,debit")
    # One wildly-out-of-pattern transaction.
    lines.append("2026-02-01,LUXURY WATCH BOUTIQUE,75000.00,debit")
    return ("\n".join(lines) + "\n").encode()


def test_detect_requires_auth(client):
    assert client.post(DETECT_URL).status_code == 401


def test_anomalies_list_requires_auth(client):
    assert client.get(ANOMALIES_URL).status_code == 401


def test_detect_reports_insufficient_data_for_few_transactions(client):
    headers = _auth_headers(client)
    small_csv = (
        b"date,description,amount,type\n"
        b"2026-01-01,SWIGGY ORDER,400,debit\n"
        b"2026-01-02,ZOMATO ORDER,420,debit\n"
    )
    client.post(IMPORTS_URL, headers=headers, files={"file": ("small.csv", io.BytesIO(small_csv), "text/csv")})
    response = client.post(DETECT_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_data"
    assert body["anomalies_found"] == 0


def test_import_triggers_automatic_detection_and_finds_the_spike(client):
    headers = _auth_headers(client)
    csv_bytes = _csv_with_n_normal_rows_plus_spike(25)
    upload = client.post(IMPORTS_URL, headers=headers, files={"file": ("history.csv", io.BytesIO(csv_bytes), "text/csv")})
    assert upload.status_code == 201

    # Detection already ran automatically as part of the import — no
    # explicit /detect call needed here.
    anomalies = client.get(ANOMALIES_URL, headers=headers)
    assert anomalies.status_code == 200
    body = anomalies.json()
    assert body["total"] >= 1
    reasons = [item["reason"] for item in body["items"]]
    assert any(reasons)

    txns = client.get(TRANSACTIONS_URL, headers=headers, params={"limit": 200}).json()["items"]
    flagged = [t for t in txns if t["is_anomaly"]]
    assert any(t["description"] == "LUXURY WATCH BOUTIQUE" for t in flagged)


def test_manual_detect_endpoint_also_works(client):
    headers = _auth_headers(client)
    csv_bytes = _csv_with_n_normal_rows_plus_spike(25)
    client.post(IMPORTS_URL, headers=headers, files={"file": ("history2.csv", io.BytesIO(csv_bytes), "text/csv")})

    response = client.post(DETECT_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["anomalies_found"] >= 1
    assert body["transactions_scanned"] >= 25


def test_anomalies_filterable_by_severity(client):
    headers = _auth_headers(client)
    csv_bytes = _csv_with_n_normal_rows_plus_spike(25)
    client.post(IMPORTS_URL, headers=headers, files={"file": ("history3.csv", io.BytesIO(csv_bytes), "text/csv")})

    response = client.get(ANOMALIES_URL, headers=headers, params={"severity": "high"})
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["severity"] == "high"


def test_get_unknown_anomaly_404(client):
    headers = _auth_headers(client)
    response = client.get(f"{ANOMALIES_URL}/000000000000000000000000", headers=headers)
    assert response.status_code == 404


def test_anomalies_scoped_to_user(client):
    headers_a = _auth_headers(client, email="anomaly_a@example.com")
    csv_bytes = _csv_with_n_normal_rows_plus_spike(25)
    client.post(IMPORTS_URL, headers=headers_a, files={"file": ("a.csv", io.BytesIO(csv_bytes), "text/csv")})

    headers_b = _auth_headers(client, email="anomaly_b@example.com")
    response_b = client.get(ANOMALIES_URL, headers=headers_b)
    assert response_b.json()["total"] == 0
