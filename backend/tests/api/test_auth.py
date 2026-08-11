REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/users/me"


def _register(client, email="ada@example.com", password="supersecret1", full_name="Ada Lovelace"):
    return client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "full_name": full_name},
    )


def test_register_creates_user(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["full_name"] == "Ada Lovelace"
    assert body["is_active"] is True
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_rejects_duplicate_email(client):
    _register(client)
    response = _register(client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_register_rejects_short_password(client):
    response = client.post(
        REGISTER_URL,
        json={"email": "short@example.com", "password": "abc", "full_name": "Short Pass"},
    )
    assert response.status_code == 422


def test_login_returns_token(client):
    _register(client)
    response = client.post(LOGIN_URL, json={"email": "ada@example.com", "password": "supersecret1"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_rejects_wrong_password(client):
    _register(client)
    response = client.post(LOGIN_URL, json={"email": "ada@example.com", "password": "wrong-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_rejects_unknown_email(client):
    response = client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "whatever1"})
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get(ME_URL)
    assert response.status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get(ME_URL, headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_current_user(client):
    _register(client, email="turing@example.com", full_name="Alan Turing")
    login_response = client.post(
        LOGIN_URL, json={"email": "turing@example.com", "password": "supersecret1"}
    )
    token = login_response.json()["access_token"]

    response = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "turing@example.com"
    assert body["full_name"] == "Alan Turing"


def test_logout_requires_auth(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401


def test_logout_succeeds_when_authenticated(client):
    _register(client, email="hopper@example.com", full_name="Grace Hopper")
    login_response = client.post(
        LOGIN_URL, json={"email": "hopper@example.com", "password": "supersecret1"}
    )
    token = login_response.json()["access_token"]

    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
