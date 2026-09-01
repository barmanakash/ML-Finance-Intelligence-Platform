import io

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
IMPORTS_URL = "/api/v1/imports"
RECURRING_URL = "/api/v1/recurring"
DETECT_URL = "/api/v1/recurring/detect"


def _auth_headers(client, email="recurringuser@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Recurring Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _csv_with_monthly_netflix(months: int = 6) -> bytes:
    lines = ["date,description,amount,type"]
    for i in range(months):
        month = (i % 12) + 1
        lines.append(f"2026-{month:02d}-05,NETFLIX SUBSCRIPTION,649.00,debit")
    return ("\n".join(lines) + "\n").encode()


def test_detect_requires_auth(client):
    assert client.post(DETECT_URL).status_code == 401


def test_recurring_list_requires_auth(client):
    assert client.get(RECURRING_URL).status_code == 401


def test_import_triggers_automatic_recurring_detection(client):
    headers = _auth_headers(client)
    csv_bytes = _csv_with_monthly_netflix(6)
    upload = client.post(
        IMPORTS_URL, headers=headers, files={"file": ("netflix.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert upload.status_code == 201

    response = client.get(RECURRING_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    merchants = [item["merchant"] for item in body["items"]]
    assert "NETFLIX SUBSCRIPTION" in merchants


def test_manual_detect_endpoint_also_works(client):
    headers = _auth_headers(client)
    csv_bytes = _csv_with_monthly_netflix(6)
    client.post(IMPORTS_URL, headers=headers, files={"file": ("n2.csv", io.BytesIO(csv_bytes), "text/csv")})

    response = client.post(DETECT_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["recurring_found"] >= 1


def test_too_few_occurrences_are_not_flagged(client):
    headers = _auth_headers(client)
    csv_bytes = (
        b"date,description,amount,type\n"
        b"2026-01-05,NETFLIX SUBSCRIPTION,649.00,debit\n"
        b"2026-02-05,NETFLIX SUBSCRIPTION,649.00,debit\n"
    )
    client.post(IMPORTS_URL, headers=headers, files={"file": ("few.csv", io.BytesIO(csv_bytes), "text/csv")})

    response = client.get(RECURRING_URL, headers=headers)
    assert response.json()["total"] == 0


def test_get_unknown_recurring_404(client):
    headers = _auth_headers(client)
    response = client.get(f"{RECURRING_URL}/000000000000000000000000", headers=headers)
    assert response.status_code == 404


def test_recurring_scoped_to_user(client):
    headers_a = _auth_headers(client, email="recurring_a@example.com")
    csv_bytes = _csv_with_monthly_netflix(6)
    client.post(IMPORTS_URL, headers=headers_a, files={"file": ("a.csv", io.BytesIO(csv_bytes), "text/csv")})

    headers_b = _auth_headers(client, email="recurring_b@example.com")
    response_b = client.get(RECURRING_URL, headers=headers_b)
    assert response_b.json()["total"] == 0
