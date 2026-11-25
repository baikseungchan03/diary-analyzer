"""별명 + PIN 로그인 로직과 세션 상태 관리."""

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
from frontend import cookie_helper

load_dotenv()

MAX_FAILS = 5
LOCK_SECONDS = 600
SESSION_DAYS = 7          # 세션 자체의 최종 만료
ROTATE_AFTER_HOURS = 1    # 이 시간이 지난 뒤 처음 쓰일 때만 토큰을 교체해요


def _hash_pin(pin, salt_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


def _hash_token(raw_token):
    """쿠키에 담는 원본 토큰과, DB에 저장하는 값을 다르게 만듭니다."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


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


def _issue_session(nickname):
    """새 세션 토큰을 발급해서 DB에 저장(해시)하고 쿠키에 원본을 담습니다."""
    raw_token = secrets.token_urlsafe(32)
    now = time.time()
    db.save_session(
        _hash_token(raw_token),
        nickname,
        expires_at=now + SESSION_DAYS * 86400,
        rotate_after=now + ROTATE_AFTER_HOURS * 3600,
    )
    cookie_helper.set_token(raw_token, SESSION_DAYS)


def _new_session(nickname):
    _issue_session(nickname)


def _restore_session():
    """쿠키의 토큰으로 자동 로그인을 시도합니다.

    - 토큰이 유효하면 그대로 로그인하고, 교체 시점이 아직 안 됐으면 그대로 둬요.
      (같은 시간대 안의 여러 탭·새로고침이 서로 방해하지 않도록)
    - 교체 시점이 지났으면, 그제서야 새 토큰으로 바꾸고 옛 토큰은
      '교체됨' 표시만 남겨요(완전히 지우지 않음).
    - 이미 '교체됨' 표시가 있는 옛 토큰이 다시 나타나면, 탈취 신호로 보고
      그 사람의 모든 세션을 강제로 끊어요(재사용 탐지).
    """
    if current_user():
        return

    raw_token = cookie_helper.get_token()
    if not raw_token:
        return

    token_hash = _hash_token(raw_token)
    session = db.get_session(token_hash)

    if session is None:
        cookie_helper.clear_token()
        return

    if session["superseded_by"] is not None:
        # 이미 교체되어 '죽은' 토큰이 다시 쓰였어요. 탈취 가능성 신호로 보고
        # 안전을 위해 그 사람의 모든 세션을 끊습니다. 다시 PIN으로 로그인해야 해요.
        db.delete_sessions_for_user(session["nickname"])
        cookie_helper.clear_token()
        return

    if session["expires_at"] <= time.time():
        db.delete_session(token_hash)
        cookie_helper.clear_token()
        return

    st.session_state["user"] = session["nickname"]

    if session["rotate_after"] <= time.time():
        # 일정 시간이 지났으니, 이번에만 새 토큰으로 교체해요.
        # 같은 시간대 안의 다른 탭은 교체 전 토큰을 그대로 계속 써도 돼서
        # 동시 접속 충돌이 거의 생기지 않아요.
        new_raw = secrets.token_urlsafe(32)
        new_hash = _hash_token(new_raw)
        now = time.time()
        db.save_session(
            new_hash,
            session["nickname"],
            expires_at=now + SESSION_DAYS * 86400,
            rotate_after=now + ROTATE_AFTER_HOURS * 3600,
        )
        db.mark_superseded(token_hash, new_hash)
        cookie_helper.set_token(new_raw, SESSION_DAYS)


def revoke_leaked_token(raw_token):
    """노출됐을 가능성이 있는 토큰(예: 주소창에서 발견)을 즉시 무효화합니다."""
    if raw_token:
        db.delete_session(_hash_token(raw_token))


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
    """로그인 상태인지 확인합니다. 쿠키로 복구도 시도해요."""
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
    db.delete_sessions_for_user(key)
    clear_session()
    st.session_state["flash"] = "계정과 일기를 모두 삭제했어요."


def clear_session():
    raw_token = cookie_helper.get_token()
    if raw_token:
        db.delete_session(_hash_token(raw_token))
        cookie_helper.clear_token()
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def logout():
    clear_session()
    st.rerun()