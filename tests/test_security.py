import pytest

from wms.auth import find_local_user
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
