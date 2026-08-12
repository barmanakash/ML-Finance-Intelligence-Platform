import io

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
IMPORTS_URL = "/api/v1/imports"
TRANSACTIONS_URL = "/api/v1/transactions"

VALID_CSV = (
    b"date,description,amount,type\n"
    b"2026-01-01,SWIGGY ORDER,438.00,debit\n"
    b"2026-01-02,SALARY,65000,credit\n"
    b"2026-01-03,AMAZON,2499,debit\n"
)


def _auth_headers(client, email="importer@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Import Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_csv_creates_import_and_transactions(client):
    headers = _auth_headers(client)
    response = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("transactions.csv", io.BytesIO(VALID_CSV), "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["total_rows"] == 3
    assert body["imported_rows"] == 3
    assert body["failed_rows"] == 0

    txns = client.get(TRANSACTIONS_URL, headers=headers)
    assert txns.status_code == 200
    txn_body = txns.json()
    assert txn_body["total"] == 3
    descriptions = {t["description"] for t in txn_body["items"]}
    assert descriptions == {"SWIGGY ORDER", "SALARY", "AMAZON"}


def test_duplicate_file_upload_rejected(client):
    headers = _auth_headers(client)
    first = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("transactions.csv", io.BytesIO(VALID_CSV), "text/csv")},
    )
    assert first.status_code == 201

    second = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("transactions.csv", io.BytesIO(VALID_CSV), "text/csv")},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_non_csv_file_rejected(client):
    headers = _auth_headers(client)
    response = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("transactions.txt", io.BytesIO(b"not a csv"), "text/plain")},
    )
    assert response.status_code == 400


def test_partial_import_reports_row_errors(client):
    headers = _auth_headers(client)
    csv_with_bad_row = (
        b"date,description,amount,type\n"
        b"2026-01-01,SWIGGY ORDER,438.00,debit\n"
        b"not-a-date,BAD ROW,100,debit\n"
        b"2026-01-03,AMAZON,2499,debit\n"
    )
    response = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("mixed.csv", io.BytesIO(csv_with_bad_row), "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "partial"
    assert body["imported_rows"] == 2
    assert body["failed_rows"] == 1
    assert body["errors"][0]["row"] == 3


def test_debit_credit_columns_supported(client):
    headers = _auth_headers(client)
    csv_debit_credit = (
        b"transaction_date,narration,debit,credit\n"
        b"2026-02-01,ELECTRICITY BILL,1500,\n"
        b"2026-02-02,SALARY CREDIT,,65000\n"
    )
    response = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("bank_export.csv", io.BytesIO(csv_debit_credit), "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["imported_rows"] == 2
    assert body["failed_rows"] == 0


def test_missing_required_columns_rejected(client):
    headers = _auth_headers(client)
    bad_csv = b"foo,bar\n1,2\n"
    response = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("bad.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert response.status_code == 422


def test_imports_require_auth(client):
    response = client.post(
        IMPORTS_URL, files={"file": ("x.csv", io.BytesIO(VALID_CSV), "text/csv")}
    )
    assert response.status_code == 401


def test_list_imports(client):
    headers = _auth_headers(client)
    client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("transactions.csv", io.BytesIO(VALID_CSV), "text/csv")},
    )
    response = client.get(IMPORTS_URL, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["filename"] == "transactions.csv"


def test_get_single_import(client):
    headers = _auth_headers(client)
    upload = client.post(
        IMPORTS_URL,
        headers=headers,
        files={"file": ("transactions.csv", io.BytesIO(VALID_CSV), "text/csv")},
    )
    import_id = upload.json()["id"]
    response = client.get(f"{IMPORTS_URL}/{import_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == import_id


def test_get_unknown_import_404(client):
    headers = _auth_headers(client)
    response = client.get(f"{IMPORTS_URL}/000000000000000000000000", headers=headers)
    assert response.status_code == 404


def test_transactions_scoped_to_user(client):
    headers_a = _auth_headers(client, email="user_a@example.com")
    client.post(
        IMPORTS_URL,
        headers=headers_a,
        files={"file": ("a.csv", io.BytesIO(VALID_CSV), "text/csv")},
    )

    headers_b = _auth_headers(client, email="user_b@example.com")
    response_b = client.get(TRANSACTIONS_URL, headers=headers_b)
    assert response_b.json()["total"] == 0

    response_a = client.get(TRANSACTIONS_URL, headers=headers_a)
    assert response_a.json()["total"] == 3


def test_transactions_require_auth(client):
    response = client.get(TRANSACTIONS_URL)
    assert response.status_code == 401
