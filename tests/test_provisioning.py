import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.lighthouse import app
from server.server_helper.auth_helper import create_access_token
from server.server_helper.db import Base, get_db


AGENT_ID = "a" * 32
AGENT_SECRET = "b" * 64


@pytest.fixture()
def isolated_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def operator_headers() -> dict[str, str]:
    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}


def agent_headers(secret: str = AGENT_SECRET) -> dict[str, str]:
    return {"Authorization": f"Agent {AGENT_ID}:{secret}"}


def provision_agent(client: TestClient):
    return client.post(
        "/provision/",
        headers=operator_headers(),
        json={
            "id": AGENT_ID,
            "credential_hash": hashlib.sha256(
                AGENT_SECRET.encode("ascii")
            ).hexdigest(),
        },
    )


def implant_payload() -> dict:
    return {
        "session": AGENT_ID,
        "hostname": "test-host",
        "username": "test-user",
        "callback_freq": 1,
        "jitter": 15,
    }


def test_provision_requires_operator_token(isolated_client):
    response = isolated_client.post(
        "/provision/",
        json={"id": AGENT_ID, "credential_hash": "c" * 64},
    )
    assert response.status_code == 401


def test_provision_and_activate_agent(isolated_client):
    provision_response = provision_agent(isolated_client)
    assert provision_response.status_code == 201
    assert provision_response.json()["id"] == AGENT_ID
    assert provision_response.json()["status"] == "provisioned"
    assert "credential_hash" not in provision_response.json()

    missing_auth = isolated_client.post("/implants/", json=implant_payload())
    assert missing_auth.status_code == 401

    wrong_secret = isolated_client.post(
        "/implants/",
        headers=agent_headers("c" * 64),
        json=implant_payload(),
    )
    assert wrong_secret.status_code == 401

    checkin = isolated_client.post(
        "/implants/",
        headers=agent_headers(),
        json=implant_payload(),
    )
    assert checkin.status_code == 200
    assert checkin.json()["session"] == AGENT_ID

    health = isolated_client.get(
        f"/health/{AGENT_ID}",
        headers=agent_headers(),
    )
    assert health.status_code == 200


def test_agent_cannot_use_another_session(isolated_client):
    assert provision_agent(isolated_client).status_code == 201

    response = isolated_client.post(
        "/implants/",
        headers=agent_headers(),
        json={**implant_payload(), "session": "c" * 32},
    )
    assert response.status_code == 403


def test_revoked_agent_is_rejected(isolated_client):
    assert provision_agent(isolated_client).status_code == 201
    assert isolated_client.post(
        "/implants/",
        headers=agent_headers(),
        json=implant_payload(),
    ).status_code == 200

    revoke = isolated_client.delete(
        f"/provision/{AGENT_ID}",
        headers=operator_headers(),
    )
    assert revoke.status_code == 200
    assert revoke.json()["status"] == "revoked"

    health = isolated_client.get(
        f"/health/{AGENT_ID}",
        headers=agent_headers(),
    )
    assert health.status_code == 401
