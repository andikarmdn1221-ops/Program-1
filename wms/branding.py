"""Aset merek Mirai yang aman dipakai di komponen HTML Streamlit."""

from base64 import b64encode
from functools import lru_cache
from pathlib import Path


LOGO_PATH = Path(__file__).resolve().parent.parent / "logo mirai 1.png"


@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    """Kembalikan logo lokal sebagai data URI agar konsisten di seluruh halaman."""
    try:
        encoded = b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:image/png;base64,{encoded}"
