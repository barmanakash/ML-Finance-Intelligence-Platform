CATEGORIES_URL = "/api/v1/categories"
REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def _auth_headers(client, email="categoryuser@example.com"):
    client.post(
        REGISTER_URL,
        json={"email": email, "password": "supersecret1", "full_name": "Category Tester"},
    )
    resp = client.post(LOGIN_URL, json={"email": email, "password": "supersecret1"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_list_requires_auth(client):
    assert client.get(CATEGORIES_URL).status_code == 401


def test_default_categories_are_seeded_on_startup(client):
    headers = _auth_headers(client)
    response = client.get(CATEGORIES_URL, headers=headers)
    assert response.status_code == 200
    items = response.json()["items"]
    names = {i["name"] for i in items}
    assert "Food" in names
    assert "Rent" in names
    assert "Other" in names
    assert all(i["is_default"] for i in items)


def test_create_custom_category(client):
    headers = _auth_headers(client)
    response = client.post(CATEGORIES_URL, headers=headers, json={"name": "Pet Care"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Pet Care"
    assert body["is_default"] is False

    listing = client.get(CATEGORIES_URL, headers=headers).json()["items"]
    assert any(i["name"] == "Pet Care" for i in listing)


def test_cannot_create_duplicate_category_name(client):
    headers = _auth_headers(client)
    client.post(CATEGORIES_URL, headers=headers, json={"name": "Pet Care"})
    response = client.post(CATEGORIES_URL, headers=headers, json={"name": "Pet Care"})
    assert response.status_code == 409


def test_cannot_create_category_matching_a_default_name(client):
    headers = _auth_headers(client)
    response = client.post(CATEGORIES_URL, headers=headers, json={"name": "Food"})
    assert response.status_code == 409


def test_can_delete_own_custom_category(client):
    headers = _auth_headers(client)
    created = client.post(CATEGORIES_URL, headers=headers, json={"name": "Hobbies"}).json()
    response = client.delete(f"{CATEGORIES_URL}/{created['id']}", headers=headers)
    assert response.status_code == 204

    listing = client.get(CATEGORIES_URL, headers=headers).json()["items"]
    assert not any(i["name"] == "Hobbies" for i in listing)


def test_cannot_delete_default_category(client):
    headers = _auth_headers(client)
    listing = client.get(CATEGORIES_URL, headers=headers).json()["items"]
    food = next(i for i in listing if i["name"] == "Food")
    response = client.delete(f"{CATEGORIES_URL}/{food['id']}", headers=headers)
    assert response.status_code == 403


def test_custom_categories_are_scoped_to_owner(client):
    headers_a = _auth_headers(client, email="cat_a@example.com")
    created = client.post(CATEGORIES_URL, headers=headers_a, json={"name": "OnlyForA"}).json()

    headers_b = _auth_headers(client, email="cat_b@example.com")
    listing_b = client.get(CATEGORIES_URL, headers=headers_b).json()["items"]
    assert not any(i["name"] == "OnlyForA" for i in listing_b)

    delete_response = client.delete(f"{CATEGORIES_URL}/{created['id']}", headers=headers_b)
    assert delete_response.status_code == 404
