"""Fail CI jika credential nyata atau secrets.toml ikut ter-commit."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_SECRET_EXAMPLES = {
    ".streamlit/secrets.example.toml",
}
PATTERNS = {
    "Telegram bot token": re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "Private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
HARDCODED_ASSIGNMENT = re.compile(
    r"""(?im)^\s*(API_SHARED_KEY|AUTH_SIGNING_KEY|TELEGRAM_BOT_TOKEN|"""
    r"""ACCOUNT_TELEGRAM_BOT_TOKEN)\s*=\s*["']([^"']+)["']"""
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    )
    return [
        ROOT / item.decode("utf-8")
        for item in output.split(b"\0")
        if item
    ]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative == ".streamlit/secrets.toml":
            findings.append(
                f"{relative}: secrets.toml produksi tidak boleh dilacak Git"
            )
            continue
        if relative in ALLOWED_SECRET_EXAMPLES or not path.is_file():
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{relative}: pola {label} terdeteksi")

        for match in HARDCODED_ASSIGNMENT.finditer(text):
            value = match.group(2).strip().lower()
            if value and not any(
                marker in value
                for marker in ("example", "contoh", "ganti", "placeholder")
            ):
                findings.append(
                    f"{relative}: {match.group(1)} tampak di-hardcode"
                )

    if findings:
        print("Pemeriksaan secrets gagal:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1

    print("Pemeriksaan secrets lulus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
