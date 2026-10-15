import hashlib
from types import SimpleNamespace

from agent import build_agent


def test_certificate_fingerprint_is_sha256():
    fingerprint = build_agent.certificate_fingerprint(
        build_agent.DEFAULT_CERT_PATH
    )
    assert len(fingerprint) == 64
    int(fingerprint, 16)


def test_provision_agent_posts_id_and_hash(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return SimpleNamespace(status_code=201, text="")

    monkeypatch.setattr(build_agent.httpx, "post", fake_post)
    build_agent.provision_agent(
        "https://localhost:8000/",
        "operator-token",
        "a" * 32,
        "b" * 64,
        build_agent.DEFAULT_CERT_PATH,
    )

    assert captured["url"] == "https://localhost:8000/provision/"
    assert captured["headers"] == {"Authorization": "Bearer operator-token"}
    assert captured["json"] == {
        "id": "a" * 32,
        "credential_hash": "b" * 64,
    }


def test_build_provisions_hash_and_stamps_plaintext_secret(monkeypatch, tmp_path):
    agent_id = "a" * 32
    agent_secret = "b" * 64
    credential_hash = hashlib.sha256(agent_secret.encode("ascii")).hexdigest()
    provisioned = {}
    command = {}

    monkeypatch.setattr(build_agent, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(
        build_agent,
        "generate_secret",
        lambda: (agent_id, agent_secret, credential_hash),
    )

    def fake_provision(server_url, token, supplied_id, supplied_hash, *args):
        provisioned.update(
            server_url=server_url,
            token=token,
            agent_id=supplied_id,
            credential_hash=supplied_hash,
        )

    def fake_run(cmd, **kwargs):
        command["value"] = cmd
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(build_agent, "provision_agent", fake_provision)
    monkeypatch.setattr(build_agent.subprocess, "run", fake_run)
    monkeypatch.setattr(build_agent, "upx_compress", lambda outfile: True)

    assert build_agent.build_galleon(
        "amd64",
        False,
        "https://localhost:8000",
        "operator-token",
        build_agent.DEFAULT_CERT_PATH,
    )

    assert provisioned == {
        "server_url": "https://localhost:8000",
        "token": "operator-token",
        "agent_id": agent_id,
        "credential_hash": credential_hash,
    }
    ldflags = command["value"][command["value"].index("-ldflags") + 1]
    assert f"AgentId={agent_id}" in ldflags
    assert f"AgentSecret={agent_secret}" in ldflags
    assert f"AgentSecret={credential_hash}" not in ldflags
    assert "ServerCertSHA256=" in ldflags


def test_failed_build_revokes_provisioned_agent(monkeypatch, tmp_path):
    agent_id = "a" * 32
    agent_secret = "b" * 64
    credential_hash = hashlib.sha256(agent_secret.encode("ascii")).hexdigest()
    revoked = []

    monkeypatch.setattr(build_agent, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(
        build_agent,
        "generate_secret",
        lambda: (agent_id, agent_secret, credential_hash),
    )
    monkeypatch.setattr(build_agent, "provision_agent", lambda *args: None)
    monkeypatch.setattr(
        build_agent,
        "revoke_agent",
        lambda server_url, token, supplied_id, *args: revoked.append(supplied_id),
    )
    monkeypatch.setattr(
        build_agent.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="compiler error",
        ),
    )

    assert not build_agent.build_galleon(
        "amd64",
        False,
        "https://localhost:8000",
        "operator-token",
        build_agent.DEFAULT_CERT_PATH,
    )
    assert revoked == [agent_id]
