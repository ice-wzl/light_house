import pytest

from httpx import codes
from fastapi.testclient import TestClient
from server.lighthouse import app

# local imports
from server.server_helper.auth_helper import Token, oauth2_scheme
from server.server_helper.auth_helper import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

from server.server_helper.user_helper import Users, UserCreate, UserRead, UserDelete
from server.server_helper.db import Base, SessionLocal

from server.server_helper.db import get_db

from server.server_helper.implant_helper import Implant, ImplantCreate, ImplantRead
from server.server_helper.tasking_helper import (
    Tasking,
    TaskingCreate,
    TaskingRead,
    TaskingDelete,
)

from server.server_helper.results_helper import (
    Results,
    ResultsCreate,
    ResultsRead,
    ResultsDelete,
)

client = TestClient(app)

def get_headers_helper():
    headers = {
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    return headers


def get_token_headers_helper():
    token = get_token_helper()
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    return headers


def get_response_helper(response):
    print(response.status_code)
    print(response.json())


def get_token_helper():
    data = {
        "grant_type": "password",
        "username": "admin",
        "password": "password",
        "scope": "",
        "client_id": "string",
        "client_secret": "string",
    }
    response = client.post("http://127.0.0.1:8000/token/", headers=get_headers_helper(), data=data)
    response_data = response.json()
    token = response_data["access_token"]
    return token


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
    print(f"Testing: test_token_methods_req(): {method.upper()}")
    response = getattr(client, method)("/token/", headers=get_headers_helper())
    if response.content:
        get_response_helper(response)
    assert response.status_code == 405
    if method != "head":
        assert response.json()["detail"] == "Method Not Allowed"


def test_token_post_req():
    print(f"Testing: test_token_post_req()")
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


@pytest.mark.parametrize(
    "method,expected_status",
    [
        ("post", codes.METHOD_NOT_ALLOWED),
        ("put", codes.METHOD_NOT_ALLOWED),
        ("options", codes.METHOD_NOT_ALLOWED),
        ("delete", codes.METHOD_NOT_ALLOWED),
        ("head", codes.METHOD_NOT_ALLOWED),
        ("put", codes.METHOD_NOT_ALLOWED),
        ("patch", codes.METHOD_NOT_ALLOWED),
    ]
)
def test_users_methods_req(method, expected_status):
    print(f"Testing: test_users_methods_req(): {method.upper()}")
    response = getattr(client, method)("/users", headers=get_token_headers_helper())
    if response.content:
        get_response_helper(response)
    assert response.status_code == 405
    if method != "head":
        assert response.json()["detail"] == "Method Not Allowed"


def test_users_get_req():
    print(f"Testing: test_users_get_req()")
    response = client.get("/users", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()[0]["username"] == "admin"


def test_users_no_token_get_req():
    print("Testing: test_userse_no_token_get_req()")
    response = client.get("/users", headers=get_headers_helper())
    get_response_helper(response)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_user_first_req():
    print(f"Testing: test_get_user_first_req()")
    response = client.get("/users/1", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"



