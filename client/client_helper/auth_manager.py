import threading
import time
from collections.abc import Callable

from jose import JWTError, jwt

from client.client_helper.user_manager import authenticate


class InMemoryAuthManager:
    def __init__(
        self,
        username: str,
        password: str,
        server: str,
        refresh_margin_seconds: int = 120,
        retry_seconds: int = 30,
        on_refresh_error: Callable[[Exception], None] | None = None,
    ):
        self._username = username
        self._password = password
        self._server = server
        self._refresh_margin_seconds = refresh_margin_seconds
        self._retry_seconds = retry_seconds
        self._on_refresh_error = on_refresh_error

        self._token = ""
        self._expires_at = 0.0
        self._refresh_at = 0.0
        self._state_lock = threading.RLock()
        self._refresh_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        token = self.refresh()
        self._thread = threading.Thread(
            target=self._refresh_loop,
            name="lighthouse-token-refresh",
            daemon=True,
        )
        self._thread.start()
        return token

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1)
        with self._state_lock:
            self._token = ""
            self._password = ""
            self._expires_at = 0.0
            self._refresh_at = 0.0

    def get_token(self) -> str:
        with self._state_lock:
            token = self._token
            expired = time.time() >= self._expires_at

        if not token or expired:
            return self.refresh()
        return token

    def refresh(self) -> str:
        with self._refresh_lock:
            token = authenticate(self._username, self._password, self._server)
            expires_at = self._token_expiration(token)
            refresh_at = max(
                time.time() + 1,
                expires_at - self._refresh_margin_seconds,
            )
            with self._state_lock:
                self._token = token
                self._expires_at = expires_at
                self._refresh_at = refresh_at
            return token

    @staticmethod
    def _token_expiration(token: str) -> float:
        try:
            expiration = jwt.get_unverified_claims(token).get("exp")
        except JWTError as exc:
            raise RuntimeError("Lighthouse returned an invalid access token") from exc

        if not isinstance(expiration, (int, float)):
            raise RuntimeError("Lighthouse access token has no expiration")
        return float(expiration)

    def _refresh_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._state_lock:
                delay = max(0.0, self._refresh_at - time.time())

            if self._stop_event.wait(delay):
                return

            try:
                self.refresh()
            except Exception as exc:
                if self._on_refresh_error is not None:
                    self._on_refresh_error(exc)
                with self._state_lock:
                    retry_at = time.time() + self._retry_seconds
                    if self._expires_at > time.time():
                        retry_at = min(self._expires_at, retry_at)
                    self._refresh_at = retry_at
