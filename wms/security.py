"""Primitif keamanan yang tidak bergantung pada UI Streamlit."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LoginRateLimiter:
    """Pembatas percobaan login lintas sesi pada satu proses aplikasi."""

    def __init__(self, max_attempts: int, window_seconds: int, lock_seconds: int):
        self.max_attempts = max(1, int(max_attempts))
        self.window_seconds = max(1, int(window_seconds))
        self.lock_seconds = max(1, int(lock_seconds))
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _key(username: str) -> str:
        return str(username or "").strip().lower() or "__anonymous__"

    def _prune(self, key: str, now: float) -> None:
        attempts = self._attempts[key]
        threshold = now - self.window_seconds
        while attempts and attempts[0] <= threshold:
            attempts.popleft()
        if not attempts:
            self._attempts.pop(key, None)

    def retry_after(self, username: str, *, now: float | None = None) -> int:
        current = time.time() if now is None else float(now)
        key = self._key(username)
        with self._lock:
            locked_until = self._locked_until.get(key, 0.0)
            if locked_until <= current:
                self._locked_until.pop(key, None)
                return 0
            return max(1, int(locked_until - current + 0.999))

    def record_failure(self, username: str, *, now: float | None = None) -> int:
        current = time.time() if now is None else float(now)
        key = self._key(username)
        with self._lock:
            self._prune(key, current)
            attempts = self._attempts[key]
            attempts.append(current)
            if len(attempts) >= self.max_attempts:
                self._locked_until[key] = current + self.lock_seconds
                attempts.clear()
                return self.lock_seconds
            return 0

    def record_success(self, username: str) -> None:
        key = self._key(username)
        with self._lock:
            self._attempts.pop(key, None)
            self._locked_until.pop(key, None)

