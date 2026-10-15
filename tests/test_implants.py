import pytest

from httpx import codes
from fastapi.testclient import TestClient
from server.lighthouse import app

from tests.helper_functions import get_token_headers_helper
from tests.helper_functions import get_response_helper
from tests.helper_functions import generate_fake_session
from tests.helper_functions import gen_fake_host_data
from tests.helper_functions import get_agent_headers_helper

client = TestClient(app)


def test_agent_checkin_req():
    print(f"\tTesting: test_agent_checkin_req()")
    response = generate_fake_session()
    get_response_helper(response)
    assert response.status_code == 200

def test_agent_checkin_missing_id():
    print(f"Testing: test_Agent_Checkin_missing_id()")
    data = {
        "session": "",
        "hostname": gen_fake_host_data(10),
        "username": gen_fake_host_data(5),
        "callback_freq": 1,
        "jitter": 15,
    }
    valid_agent = generate_fake_session().json()["session"]
    response = client.post(
        "/implants/",
        headers=get_agent_headers_helper(valid_agent),
        json=data,
    )
    get_response_helper(response)
    assert response.status_code == 403
    assert response.json()["detail"] == "Agent cannot use this session"

def test_get_implants_req():
    print(f"Testing: test_Get_implants_req()")
    response = client.get("/implants/", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200

def test_get_implant_session():
    print(f"Testing: test_get_implant_session()")
    fake = generate_fake_session()
    session_id = fake.json()["session"]
    print(session_id)
    response = client.get(f"/implants/{session_id}", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200
    assert response.json()["session"] == session_id

@pytest.mark.parametrize(
    "method,expected_status",
    [
        ("put", codes.METHOD_NOT_ALLOWED),
        ("options", codes.METHOD_NOT_ALLOWED),
        ("delete", codes.METHOD_NOT_ALLOWED),
        ("head", codes.METHOD_NOT_ALLOWED),
        ("put", codes.METHOD_NOT_ALLOWED),
        ("patch", codes.METHOD_NOT_ALLOWED),
    ]
)
def test_alt_methods_implants(method, expected_status):
    print(f"Testing: test_alt_methods_implants()")
    response = getattr(client, method)("/implants/", headers=get_token_headers_helper())
    if response.content:
        get_response_helper(response)
    assert response.status_code == 405
    if method != "head":
        assert response.json()["detail"] == "Method Not Allowed"
