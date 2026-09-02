import io

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
IMPORTS_URL = "/api/v1/imports"
TRANSACTIONS_URL = "/api/v1/transactions"


def _auth_headers(client, email="txnuser@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Txn Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _seed_transactions(client, headers) -> None:
    csv_bytes = (
        b"date,description,amount,type\n"
        b"2026-01-01,SWIGGY ORDER,438.00,debit\n"
        b"2026-01-02,SALARY,65000.00,credit\n"
        b"2026-01-03,AMAZON PURCHASE,2499.00,debit\n"
        b"2026-01-04,UBER TRIP,320.00,debit\n"
    )
    client.post(IMPORTS_URL, headers=headers, files={"file": ("seed.csv", io.BytesIO(csv_bytes), "text/csv")})


def test_list_requires_auth(client):
    assert client.get(TRANSACTIONS_URL).status_code == 401


def test_list_returns_all_imported_transactions(client):
    headers = _auth_headers(client)
    _seed_transactions(client, headers)

    response = client.get(TRANSACTIONS_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 4


def test_filter_by_transaction_type(client):
    headers = _auth_headers(client)
    _seed_transactions(client, headers)

    response = client.get(TRANSACTIONS_URL, headers=headers, params={"transaction_type": "credit"})
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["description"] == "SALARY"


def test_search_matches_description_case_insensitively(client):
    headers = _auth_headers(client)
    _seed_transactions(client, headers)

    response = client.get(TRANSACTIONS_URL, headers=headers, params={"search": "amazon"})
    body = response.json()
    assert body["total"] == 1
    assert "AMAZON" in body["items"][0]["description"]


def test_pagination_limits_results(client):
    headers = _auth_headers(client)
    _seed_transactions(client, headers)

    response = client.get(TRANSACTIONS_URL, headers=headers, params={"skip": 0, "limit": 2})
    body = response.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2


def test_get_single_transaction(client):
    headers = _auth_headers(client)
    _seed_transactions(client, headers)
    listing = client.get(TRANSACTIONS_URL, headers=headers).json()["items"]
    txn_id = listing[0]["id"]

    response = client.get(f"{TRANSACTIONS_URL}/{txn_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == txn_id


def test_get_unknown_transaction_404(client):
    headers = _auth_headers(client)
    response = client.get(f"{TRANSACTIONS_URL}/000000000000000000000000", headers=headers)
    assert response.status_code == 404


def test_patch_updates_category_and_marks_confirmed(client):
    headers = _auth_headers(client)
    _seed_transactions(client, headers)
    listing = client.get(TRANSACTIONS_URL, headers=headers).json()["items"]
    txn_id = listing[0]["id"]

    response = client.patch(f"{TRANSACTIONS_URL}/{txn_id}", headers=headers, json={"category": "Travel"})
    assert response.status_code == 200
    assert response.json()["category"] == "Travel"

    refetched = client.get(f"{TRANSACTIONS_URL}/{txn_id}", headers=headers).json()
    assert refetched["category"] == "Travel"


def test_patch_unknown_transaction_404(client):
    headers = _auth_headers(client)
    response = client.patch(
        f"{TRANSACTIONS_URL}/000000000000000000000000", headers=headers, json={"category": "Travel"}
    )
    assert response.status_code == 404


def test_transactions_scoped_to_user(client):
    headers_a = _auth_headers(client, email="txn_a@example.com")
    _seed_transactions(client, headers_a)

    headers_b = _auth_headers(client, email="txn_b@example.com")
    response_b = client.get(TRANSACTIONS_URL, headers=headers_b)
    assert response_b.json()["total"] == 0
