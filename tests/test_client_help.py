from client.client_helper import session_manager


def test_pid_hider_help_is_routed(monkeypatch):
    called = []
    monkeypatch.setattr(
        session_manager,
        "print_pid_hider_help",
        lambda: called.append(True),
    )

    session_manager.handle_help(["pid_hider"])
    assert called == [True]


def test_pid_hider_requires_exactly_two_numeric_arguments(monkeypatch):
    sent = []
    monkeypatch.setattr(session_manager, "print_formatted_text", lambda *args: None)
    monkeypatch.setattr(
        session_manager,
        "send_task",
        lambda *args: sent.append(args),
    )

    session_manager.handle_pid_hider("token", "server", "session", ["1234"])
    session_manager.handle_pid_hider(
        "token",
        "server",
        "session",
        ["1234", "0", "extra"],
    )
    session_manager.handle_pid_hider(
        "token",
        "server",
        "session",
        ["not-a-pid", "0"],
    )
    assert sent == []

    session_manager.handle_pid_hider(
        "token",
        "server",
        "session",
        ["1234", "0"],
    )
    assert sent == [
        ("token", "server", "session", "pid_hider", "1234 0")
    ]
