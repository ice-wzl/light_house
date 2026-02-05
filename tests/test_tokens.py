import pytest

from httpx import codes
from fastapi.testclient import TestClient

from server.lighthouse import app

from tests.helper_functions import get_headers_helper
from tests.helper_functions import get_response_helper

client = TestClient(app)

@pytest.mark.parametrize(
    "method,expected_status",
    [
        ("get", codes.METHOD_NOT_ALLOWED),
        ("put", codes.METHOD_NOT_ALLOWED),
        ("options", codes.METHOD_NOT_ALLOWED),
        ("delete", codes.METHOD_NOT_ALLOWED),
        ("head", codes.METHOD_NOT_ALLOWED),
        ("put", codes.METHOD_NOT_ALLOWED),
        ("patch", codes.METHOD_NOT_ALLOWED),
    ]
)
def test_token_methods_req(method, expected_status):
    print(f"\nTesting: test_token_methods_req(): {method.upper()}")
    response = getattr(client, method)("/token/", headers=get_headers_helper())
    if response.content:
        get_response_helper(response)
    assert response.status_code == 405
    if method != "head":
        assert response.json()["detail"] == "Method Not Allowed"

def test_token_post_req():
    print(f"\nTesting: test_token_post_req()")
    data = {
        "grant_type": "password",
        "username": "admin",
        "password": "password",
        "scope": "",
        "client_id": "string",
        "client_secret": "string",
    }
    response = client.post("http://127.0.0.1:8000/token/", headers=get_headers_helper(), data=data)
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()["access_token"] is not None

