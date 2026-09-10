import pytest

from wms.auth import (
    _parse_pbkdf2_hash,
    find_local_user,
    generate_pbkdf2_hash,
    password_matches,
)
from wms.security import LoginRateLimiter


def test_rate_limiter_blocks_across_attempts():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=60, lock_seconds=120)
    assert limiter.record_failure("Andika", now=100) == 0
    assert limiter.record_failure("andika", now=101) == 0
    assert limiter.record_failure("ANDIKA", now=102) == 120
    assert limiter.retry_after("andika", now=103) == 119


def test_rate_limiter_success_clears_state():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60, lock_seconds=120)
    limiter.record_failure("staff", now=100)
    limiter.record_success("staff")
    assert limiter.retry_after("staff", now=101) == 0
    assert limiter.record_failure("staff", now=102) == 0


def test_old_attempts_leave_sliding_window():
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=10, lock_seconds=30)
    limiter.record_failure("staff", now=100)
    assert limiter.record_failure("staff", now=111) == 0


def test_rate_limiter_bounds_tracked_identity_memory():
    limiter = LoginRateLimiter(
        max_attempts=3,
        window_seconds=60,
        lock_seconds=120,
        max_identities=100,
    )
    for index in range(150):
        limiter.record_failure(f"user-{index}", now=100)
    assert len(limiter._last_seen) <= 100


def test_identity_flood_does_not_evict_locked_account():
    limiter = LoginRateLimiter(
        max_attempts=3,
        window_seconds=60,
        lock_seconds=120,
        max_identities=100,
    )
    limiter.record_failure("target", now=100)
    limiter.record_failure("target", now=101)
    limiter.record_failure("target", now=102)

    for index in range(150):
        limiter.record_failure(f"spray-{index}", now=103)

    assert limiter.retry_after("target", now=104) == 118


def test_identity_overflow_is_rate_limited_as_one_bucket():
    limiter = LoginRateLimiter(
        max_attempts=2,
        window_seconds=60,
        lock_seconds=30,
        max_identities=100,
    )
    for index in range(100):
        limiter.record_failure(f"known-{index}", now=100)

    assert limiter.record_failure("overflow-a", now=101) == 0
    assert limiter.record_failure("overflow-b", now=102) == 30
    assert limiter.retry_after("overflow-c", now=103) == 29


def test_local_user_lookup_is_case_insensitive():
    username, config = find_local_user({"Andika": {"role": "Developer"}}, "  ANDIKA  ")
    assert username == "Andika"
    assert config["role"] == "Developer"


def test_local_user_lookup_rejects_ambiguous_configuration():
    with pytest.raises(RuntimeError, match="duplikat"):
        find_local_user(
            {
                "Andika": {"role": "Developer"},
                "andika": {"role": "Staff"},
            },
            "andika",
        )


def test_local_pbkdf2_hash_is_structurally_validated():
    password_hash = generate_pbkdf2_hash("password-yang-kuat", iterations=200_000)
    assert _parse_pbkdf2_hash(password_hash)
    assert password_matches(
        "password-yang-kuat", {"password_hash": password_hash}
    )
    assert not password_matches("salah", {"password_hash": password_hash})
    assert _parse_pbkdf2_hash("pbkdf2_sha256$10$aa$bb") is None
    assert (
        _parse_pbkdf2_hash(
            "pbkdf2_sha256$1000001$" + "aa" * 16 + "$" + "bb" * 32
        )
        is None
    )
