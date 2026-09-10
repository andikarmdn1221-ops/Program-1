"""Primitif keamanan yang tidak bergantung pada UI Streamlit."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LoginRateLimiter:
    """Pembatas percobaan login lintas sesi pada satu proses aplikasi."""

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        lock_seconds: int,
        max_identities: int = 10_000,
    ):
        self.max_attempts = max(1, int(max_attempts))
        self.window_seconds = max(1, int(window_seconds))
        self.lock_seconds = max(1, int(lock_seconds))
        self.max_identities = max(100, int(max_identities))
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}
        self._last_seen: dict[str, float] = {}
        self._overflow_attempts: deque[float] = deque()
        self._overflow_locked_until = 0.0
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

    def _cleanup_stale(self, now: float) -> None:
        """Buang identitas kedaluwarsa tanpa menghapus akun yang masih terkunci."""
        for tracked_key in list(self._last_seen):
            if self._locked_until.get(tracked_key, 0.0) > now:
                continue
            self._locked_until.pop(tracked_key, None)
            self._prune(tracked_key, now)
            if tracked_key not in self._attempts:
                self._last_seen.pop(tracked_key, None)

    @staticmethod
    def _retry_seconds(locked_until: float, now: float) -> int:
        if locked_until <= now:
            return 0
        return max(1, int(locked_until - now + 0.999))

    def _prune_overflow(self, now: float) -> None:
        threshold = now - self.window_seconds
        while self._overflow_attempts and self._overflow_attempts[0] <= threshold:
            self._overflow_attempts.popleft()

    def _record_overflow_failure(self, now: float) -> int:
        """Batasi percobaan identitas baru saat tabel utama sudah penuh."""
        self._prune_overflow(now)
        self._overflow_attempts.append(now)
        if len(self._overflow_attempts) >= self.max_attempts:
            self._overflow_locked_until = now + self.lock_seconds
            self._overflow_attempts.clear()
            return self.lock_seconds
        return 0

    def retry_after(self, username: str, *, now: float | None = None) -> int:
        current = time.time() if now is None else float(now)
        key = self._key(username)
        with self._lock:
            if key not in self._last_seen:
                if len(self._last_seen) >= self.max_identities:
                    self._cleanup_stale(current)
                if len(self._last_seen) >= self.max_identities:
                    retry = self._retry_seconds(
                        self._overflow_locked_until, current
                    )
                    if not retry:
                        self._overflow_locked_until = 0.0
                        self._prune_overflow(current)
                    return retry
                return 0

            locked_until = self._locked_until.get(key, 0.0)
            if locked_until <= current:
                self._locked_until.pop(key, None)
                self._prune(key, current)
                if not self._attempts.get(key):
                    self._attempts.pop(key, None)
                    self._last_seen.pop(key, None)
                return 0
            return self._retry_seconds(locked_until, current)

    def record_failure(self, username: str, *, now: float | None = None) -> int:
        current = time.time() if now is None else float(now)
        key = self._key(username)
        with self._lock:
            if key not in self._last_seen:
                if len(self._last_seen) >= self.max_identities:
                    self._cleanup_stale(current)
                if len(self._last_seen) >= self.max_identities:
                    return self._record_overflow_failure(current)
            self._last_seen[key] = current
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
            self._last_seen.pop(key, None)
