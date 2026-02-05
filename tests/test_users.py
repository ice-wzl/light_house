import pytest
import string 
import random 

from httpx import codes
from fastapi.testclient import TestClient

from server.lighthouse import app

from tests.helper_functions import get_token_headers_helper
from tests.helper_functions import get_response_helper
from tests.helper_functions import get_headers_helper
from tests.helper_functions import gen_fake_host_data
from tests.helper_functions import create_user_helper

client = TestClient(app)

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
    print(f"\nTesting: test_users_methods_req(): {method.upper()}")
    response = getattr(client, method)("/users", headers=get_token_headers_helper())
    if response.content:
        get_response_helper(response)
    assert response.status_code == 405
    if method != "head":
        assert response.json()["detail"] == "Method Not Allowed"


def test_users_get_req():
    print(f"\nTesting: test_users_get_req()")
    response = client.get("/users", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()[0]["username"] == "admin"


def test_users_no_token_get_req():
    print(f"\nTesting: test_users_no_token_get_req()")
    response = client.get("/users", headers=get_headers_helper())
    get_response_helper(response)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_user_first_req():
    print(f"\nTesting: test_get_user_first_req()")
    response = client.get("/users/1", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_get_user_not_exist_req():
    print(f"\nTesting: test_get_user_not_exist_req()")
    response = client.get("/users/200", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

def test_user_create_no_username_req():
    print(f"\nTesting: test_user_create_no_username_req()")
    data = {
        "username": '',
        "password": 'abc123',
    }
    response = client.post("/users/create", headers=get_token_headers_helper(), json=data)
    get_response_helper(response)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username cannot be blank"


def test_user_create_no_password_req():
    print(f"\nTesting: test_user_create_no_password_req()")
    chars = string.ascii_lowercase
    random_username = ''.join(random.choices(chars, k=6))
    data = {
        "username": random_username,
        "password": '',
    }
    response = client.post("/users/create", headers=get_token_headers_helper(), json=data)
    get_response_helper(response)
    assert response.status_code == 400
    assert response.json()["detail"] == "Password cannot be less than 8 characters"


def test_user_create_no_token():
    print(f"\nTesting: test_user_create_no_token()")
    data = {
        "username": 'system',
        "password": 'abc123',
    }
    response = client.post("/users/create", headers=get_headers_helper(), json=data)
    get_response_helper(response)
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

    
def test_user_already_exists_req():
    print(f"\nTesting: test_user_already_exists_req()")
    data = {
        "username": "admin",
        "password": "password",
    }
    response = client.post("/users/create", headers=get_token_headers_helper(), json=data)
    get_response_helper(response)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"


def test_create_user_req():
    print(f"\tTesting: test_create_user_req()")
    username = gen_fake_host_data(6) 
    password = "abcdefgh"
    data = {
        "username": username,
        "password": password,
    }
    response = client.post("/users/create", headers=get_token_headers_helper(), json=data)
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()["username"] == username
    assert response.json()["password"] == password
    assert len(response.json()["created_at"]) > 0

def test_delete_user_by_username_req():
    print(f"\tTesting: test_detest_delete_user_by_username_reqlete_user_req()")
    fake_user = create_user_helper()
    response = client.delete(f"/users/delete/username/{fake_user}", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200