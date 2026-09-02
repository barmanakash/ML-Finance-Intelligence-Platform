import io

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
IMPORTS_URL = "/api/v1/imports"
INSIGHTS_URL = "/api/v1/insights"
GENERATE_URL = "/api/v1/insights/generate"


def _auth_headers(client, email="insightuser@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Insight Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _multi_month_csv() -> bytes:
    lines = ["date,description,amount,type"]
    # Four months of Food spending, strictly increasing, to reliably
    # trigger category_increase / category_share / consecutive_increase.
    for month, amount in zip([1, 2, 3, 4], [200, 300, 400, 900]):
        lines.append(f"2026-{month:02d}-10,RESTAURANT,{amount}.00,debit")
    # A monthly Netflix subscription across the same four months, to
    # trigger recurring detection -> the recurring_count insight.
    for month in [1, 2, 3, 4]:
        lines.append(f"2026-{month:02d}-05,NETFLIX SUBSCRIPTION,649.00,debit")
    return ("\n".join(lines) + "\n").encode()


def test_generate_requires_auth(client):
    assert client.post(GENERATE_URL).status_code == 401


def test_insights_list_requires_auth(client):
    assert client.get(INSIGHTS_URL).status_code == 401


def test_import_triggers_automatic_insight_generation(client):
    headers = _auth_headers(client)
    csv_bytes = _multi_month_csv()
    upload = client.post(
        IMPORTS_URL, headers=headers, files={"file": ("multi.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    assert upload.status_code == 201

    response = client.get(INSIGHTS_URL, headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    types_found = {i["type"] for i in items}
    # category_increase (Food jumped 900 vs 400 = +125%) and recurring_count
    # (4 monthly Netflix charges) are both deterministic given this dataset.
    assert "category_increase" in types_found
    assert "recurring_count" in types_found


def test_manual_generate_endpoint_reports_count(client):
    headers = _auth_headers(client)
    csv_bytes = _multi_month_csv()
    client.post(IMPORTS_URL, headers=headers, files={"file": ("m2.csv", io.BytesIO(csv_bytes), "text/csv")})

    response = client.post(GENERATE_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["insights_found"] >= 1


def test_fresh_user_has_no_insights(client):
    headers = _auth_headers(client, email="fresh_insights@example.com")
    response = client.get(INSIGHTS_URL, headers=headers)
    assert response.json()["items"] == []


def test_insights_scoped_to_user(client):
    headers_a = _auth_headers(client, email="insight_a@example.com")
    csv_bytes = _multi_month_csv()
    client.post(IMPORTS_URL, headers=headers_a, files={"file": ("a.csv", io.BytesIO(csv_bytes), "text/csv")})

    headers_b = _auth_headers(client, email="insight_b@example.com")
    response_b = client.get(INSIGHTS_URL, headers=headers_b)
    assert response_b.json()["items"] == []
