import json
from myapp import app

client = app.test_client()

def test_login_ok():
    resp = client.post(
        "/login",
        data=json.dumps({"username": "admin", "password": "1234"}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert "Access granted" in resp.get_json()["message"]

def test_login_invalid_credentials():
    resp = client.post(
        "/login",
        data=json.dumps({"username": "admin", "password": "0000"}),
        content_type="application/json",
    )
    assert resp.status_code == 401
    assert "Invalid credentials" in resp.get_json()["error"]

def test_login_missing_fields():
    resp = client.post(
        "/login",
        data=json.dumps({"username": "", "password": ""}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "Missing username or password" in resp.get_json()["error"]


