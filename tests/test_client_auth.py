import time
import threading
from types import SimpleNamespace

import pytest
from jose import jwt

from client.client_helper import auth_manager
from client.client_helper.user_manager import AuthenticationError, authenticate


def make_token(seconds: int = 300) -> str:
    return jwt.encode(
        {"sub": "admin", "exp": time.time() + seconds},
        "test-key",
        algorithm="HS256",
    )


def test_authenticate_returns_token_without_writing_file(monkeypatch, tmp_path):
    token = make_token()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "client.client_helper.user_manager.httpx.post",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=200,
            text="",
            json=lambda: {"access_token": token},
        ),
    )

    assert authenticate("admin", "password", "localhost:8000") == token
    assert not (tmp_path / ".auth-token").exists()


def test_authenticate_raises_for_invalid_credentials(monkeypatch):
    monkeypatch.setattr(
        "client.client_helper.user_manager.httpx.post",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=401,
            text='{"detail":"Incorrect username or password"}',
        ),
    )

    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        authenticate("admin", "wrong", "localhost:8000")


def test_in_memory_manager_refreshes_and_never_uses_disk(monkeypatch, tmp_path):
    tokens = [make_token(), make_token()]
    calls = []

    def fake_authenticate(username, password, server):
        calls.append((username, password, server))
        return tokens.pop(0)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auth_manager, "authenticate", fake_authenticate)
    manager = auth_manager.InMemoryAuthManager(
        "admin",
        "password",
        "localhost:8000",
    )

    first = manager.start()
    second = manager.refresh()
    manager.stop()

    assert first != ""
    assert second != ""
    assert len(calls) == 2
    assert not (tmp_path / ".auth-token").exists()


def test_in_memory_manager_rejects_token_without_expiration(monkeypatch):
    token = jwt.encode({"sub": "admin"}, "test-key", algorithm="HS256")
    monkeypatch.setattr(auth_manager, "authenticate", lambda *args: token)
    manager = auth_manager.InMemoryAuthManager(
        "admin",
        "password",
        "localhost:8000",
    )

    with pytest.raises(RuntimeError, match="no expiration"):
        manager.start()


def test_in_memory_manager_refreshes_automatically(monkeypatch):
    refreshed = threading.Event()
    call_count = 0

    def fake_authenticate(*args):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            refreshed.set()
        return make_token(2)

    monkeypatch.setattr(auth_manager, "authenticate", fake_authenticate)
    manager = auth_manager.InMemoryAuthManager(
        "admin",
        "password",
        "localhost:8000",
        refresh_margin_seconds=1,
    )
    manager.start()
    try:
        assert refreshed.wait(timeout=3)
    finally:
        manager.stop()
