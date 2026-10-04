"""Per-visitor identity.

Local use keeps one shared profile (user 1) so a browser refresh never loses your CV.
On Streamlit Community Cloud (or with PRIVATE_SESSIONS=1) every visitor gets a private guest profile,
so one visitor never sees another visitor's CV, profile or documents.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


def private_mode() -> bool:
    flag = os.getenv("PRIVATE_SESSIONS", "").strip().lower()
    if flag in _TRUE:
        return True
    if flag in _FALSE:
        return False
    # Streamlit Community Cloud runs apps from /mount/src/<repo>
    return str(Path(__file__).resolve()).startswith("/mount/src")


def ensure_session_user() -> int:
    """Create (once per browser session) and return this visitor's user id."""
    import streamlit as st
    uid = st.session_state.get("current_user_id")
    if uid and (uid != 1 or not private_mode()):
        return int(uid)
    if not private_mode():
        st.session_state["current_user_id"] = 1
        return 1
    from database.db import create_guest_user, purge_old_guests
    try:
        purge_old_guests(days=2)
    except Exception:
        pass
    uid = create_guest_user(uuid.uuid4().hex)
    st.session_state["current_user_id"] = uid
    return uid


def user_id() -> int:
    try:
        import streamlit as st
        return int(st.session_state.get("current_user_id") or 1)
    except Exception:
        return 1


def user_upload_dir() -> Path:
    """Uploads live in a per-user folder so two visitors uploading 'cv.pdf' never collide."""
    from config.settings import UPLOAD_DIR
    path = UPLOAD_DIR / f"u{user_id()}"
    path.mkdir(parents=True, exist_ok=True)
    return path
