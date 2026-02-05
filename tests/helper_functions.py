import pytest
import string 
import random 

from fastapi.testclient import TestClient
from server.lighthouse import app

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

def gen_fake_host_data(length: int):
    chars = string.ascii_letters + string.digits
    random_data = ''.join(random.choices(chars, k=length))
    return random_data

def gen_fake_session_name():
    chars = string.hexdigits
    random_data = ''.join(random.choices(chars, k=8))
    return random_data

def generate_fake_session():
    data = {
        "session": gen_fake_session_name(),
        "hostname": gen_fake_host_data(8),
        "username": gen_fake_host_data(5),
        "callback_freq": 1,
        "jitter": 15,
    }
    response = client.post("/implants/", json=data)
    return response

def create_user_helper():
    username = gen_fake_host_data(6) 
    password = "abcdefgh"
    data = {
        "username": username,
        "password": password,
    }
    response = client.post("/users/create", headers=get_token_headers_helper(), json=data)
    return response.json()["username"]


def get_implant_session_helper():
    implants_all = client.get("/implants/", headers=get_token_headers_helper())
    session_id = implants_all.json()[0]["session"]
    response = client.get(f"/implants/{session_id}", headers=get_token_headers_helper())
    return response.json()["session"], response.json()["last_checkin"]



def get_implants_req_helper():
    response = client.get("/implants/", headers=get_token_headers_helper())
    return get_response_helper(response)