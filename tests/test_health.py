import pytest

from httpx import codes
from fastapi.testclient import TestClient
from server.lighthouse import app

from tests.helper_functions import get_token_headers_helper
from tests.helper_functions import get_implant_session_helper
from tests.helper_functions import get_response_helper
from tests.helper_functions import generate_fake_session

client = TestClient(app)

def test_health_checkin():
    print(f"Testing: test_health_checkin()")
    (implant_session_name, implant_last_checkin) = get_implant_session_helper()
    response = client.get(f"/health/{implant_session_name}", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.json()["session"] == implant_session_name
    assert response.json()["last_checkin"] != implant_last_checkin

def test_health_checkin_not_found():
    print(f"Testing: test_health_checkin_not_found()")
    response = client.get(f"/health/aaaaaa", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 404

def test_health_implant_death_req_not_found():
    print(f"Testing: test_health_implant_death_req()")
    response = client.get(f"/health/d/aaaaaa", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 404

def test_health_implant_death_req():
    print(f"Testing: test_health_implant_death_req()")
    implant_to_kill = generate_fake_session()
    implant_to_kill_session = implant_to_kill.json()["session"]
    implant_to_kill_alive = implant_to_kill.json()["alive"]
    assert implant_to_kill_alive == True
    response = client.get(f"/health/d/{implant_to_kill_session}", headers=get_token_headers_helper())
    get_response_helper(response)
    assert response.status_code == 200