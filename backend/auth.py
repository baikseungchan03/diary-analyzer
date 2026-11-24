"""별명 + PIN 로그인 로직과 세션 상태 관리. 화면 그리기는 frontend/auth_ui.py에 있어요."""

import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from . import db
from .config import CONSENT_VERSION
from .storage import delete_user_files, is_valid_nickname

load_dotenv()

MAX_FAILS = 5
LOCK_SECONDS = 600
SESSION_DAYS = 7


def _hash_pin(pin, salt_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


def _check_pin(key, pin):
    acc = db.get_account(key)
    wrong = "별명이나 PIN이 맞지 않아요."
    if acc is None:
        return wrong

    now = time.time()
    if acc.get("locked_until", 0) > now:
        wait = int((acc["locked_until"] - now) / 60) + 1
        return f"시도가 너무 많아서 잠겼어요. 약 {wait}분 뒤에 다시 해보세요."

    if hmac.compare_digest(_hash_pin(pin, acc["salt"]), acc["hash"]):
        db.update_account(key, fails=0, locked_until=0)
        return None

    fails = acc.get("fails", 0) + 1
    locked_until = now + LOCK_SECONDS if fails >= MAX_FAILS else acc.get("locked_until", 0)
    if fails >= MAX_FAILS:
        fails = 0
    db.update_account(key, fails=fails, locked_until=locked_until)
    return wrong


def _new_session(nickname):
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + SESSION_DAYS * 86400
    db.save_session(token, nickname, expires_at)
    st.query_params["token"] = token


def _restore_session():
    if current_user():
        return
    token = st.query_params.get("token")
    if not token:
        return
    session = db.get_session(token)
    if session and session["expires_at"] > time.time():
        st.session_state["user"] = session["nickname"]
    else:
        db.delete_session(token)
        del st.query_params["token"]


# ---------- frontend/auth_ui.py가 부르는 함수 ----------
def signup(nickname, pin, pin2, code):
    """가입합니다. 문제가 있으면 안내 문구를, 성공하면 None을 돌려줘요."""
    invite = os.getenv("INVITE_CODE", "")
    if not invite:
        return "초대 코드가 설정되지 않아 가입을 막아뒀어요. (운영자 설정 필요)"
    if not hmac.compare_digest(code.encode("utf-8"), invite.encode("utf-8")):
        return "초대 코드가 달라요."

    key = nickname.strip().lower()
    if not is_valid_nickname(key):
        return "별명은 2~20자의 한글, 영문, 숫자, _, - 만 쓸 수 있어요."
    if not re.fullmatch(r"[0-9]{4,6}", pin):
        return "PIN은 숫자 4~6자리여야 해요."
    if pin != pin2:
        return "PIN 두 번이 서로 달라요."

    salt = secrets.token_hex(16)
    created = db.create_account(key, salt, _hash_pin(pin, salt))
    if not created:
        return "이미 있는 별명이에요."
    return None


def login(nickname, pin):
    """로그인합니다. 문제가 있으면 안내 문구를, 성공하면 None을 돌려줘요."""
    key = nickname.strip().lower()
    err = _check_pin(key, pin)
    if err is None:
        st.session_state["user"] = key
        _new_session(key)
    return err


def is_authenticated():
    """로그인 상태인지 확인합니다. 주소창 토큰으로 복구도 시도해요."""
    _restore_session()
    return current_user() is not None


# ---------- 다른 모든 파일에서 쓰는 함수 (기존과 동일) ----------
def current_user():
    return st.session_state.get("user")


def current_user_dir():
    return current_user()


def verify_pin(pin):
    return _check_pin(current_user(), pin)


def has_consent():
    acc = db.get_account(current_user())
    consent = (acc or {}).get("consent", {})
    return consent.get("version") == CONSENT_VERSION


def consent_time():
    acc = db.get_account(current_user())
    consent = (acc or {}).get("consent", {})
    return consent.get("at")


def give_consent():
    db.update_account(
        current_user(),
        consent_version=CONSENT_VERSION,
        consent_at=datetime.now().isoformat(timespec="seconds"),
    )


def delete_account():
    key = current_user()
    delete_user_files(key)
    db.delete_account(key)
    clear_session()
    st.session_state["flash"] = "계정과 일기를 모두 삭제했어요."


def clear_session():
    token = st.query_params.get("token")
    if token:
        db.delete_session(token)
        del st.query_params["token"]
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def logout():
    clear_session()
    st.rerun()