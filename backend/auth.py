"""별명 + PIN으로 사용자를 구분하고, 동의 여부를 기록합니다. (시범용 간이 방식)"""

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from .config import ACCOUNTS_FILE, CONSENT_VERSION, DATA_DIR
from .storage import delete_user_files, is_valid_nickname

load_dotenv()

MAX_FAILS = 5        # 연속 5번 틀리면
LOCK_SECONDS = 600   # 10분 동안 잠급니다


# ---------- 계정 파일 ----------
def _load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_accounts(accounts):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def _hash_pin(pin, salt_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), 200_000
    ).hex()


# ---------- 가입과 로그인 ----------
def _signup(nickname, pin, pin2, code):
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

    accounts = _load_accounts()
    if key in accounts:
        return "이미 있는 별명이에요."

    salt = secrets.token_hex(16)
    accounts[key] = {
        "salt": salt,
        "hash": _hash_pin(pin, salt),
        "fails": 0,
        "locked_until": 0,
    }
    _save_accounts(accounts)
    return None


def _check_pin(key, pin):
    """PIN이 맞는지 확인합니다. 문제가 있으면 안내 문구를, 맞으면 None을 돌려줘요."""
    accounts = _load_accounts()
    acc = accounts.get(key)
    wrong = "별명이나 PIN이 맞지 않아요."
    if acc is None:
        return wrong

    now = time.time()
    if acc.get("locked_until", 0) > now:
        wait = int((acc["locked_until"] - now) / 60) + 1
        return f"시도가 너무 많아서 잠겼어요. 약 {wait}분 뒤에 다시 해보세요."

    if hmac.compare_digest(_hash_pin(pin, acc["salt"]), acc["hash"]):
        acc["fails"] = 0
        acc["locked_until"] = 0
        _save_accounts(accounts)
        return None

    acc["fails"] = acc.get("fails", 0) + 1
    if acc["fails"] >= MAX_FAILS:
        acc["locked_until"] = now + LOCK_SECONDS
        acc["fails"] = 0
    _save_accounts(accounts)
    return wrong


def _login(nickname, pin):
    """로그인합니다. 문제가 있으면 안내 문구를, 성공하면 None을 돌려줘요."""
    key = nickname.strip().lower()
    err = _check_pin(key, pin)
    if err is None:
        st.session_state["user"] = key
    return err


# ---------- 다른 파일에서 쓰는 함수 ----------
def current_user():
    return st.session_state.get("user")


def current_user_dir():
    return current_user()


def verify_pin(pin):
    """지금 로그인한 사람의 PIN을 다시 확인합니다. (삭제 같은 중요한 작업 전에)"""
    return _check_pin(current_user(), pin)


def has_consent():
    """현재 동의 문구 버전에 동의했는지 알려줍니다."""
    acc = _load_accounts().get(current_user(), {})
    return acc.get("consent", {}).get("version") == CONSENT_VERSION


def consent_time():
    acc = _load_accounts().get(current_user(), {})
    return acc.get("consent", {}).get("at")


def give_consent():
    accounts = _load_accounts()
    key = current_user()
    if key in accounts:
        accounts[key]["consent"] = {
            "version": CONSENT_VERSION,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
        _save_accounts(accounts)


def delete_account():
    """일기 폴더와 계정 정보를 모두 지우고 로그아웃 상태로 만듭니다."""
    key = current_user()
    delete_user_files(key)
    accounts = _load_accounts()
    accounts.pop(key, None)
    _save_accounts(accounts)
    clear_session()
    st.session_state["flash"] = "계정과 일기를 모두 삭제했어요."


def clear_session():
    # 앞 사람의 입력 내용이 남지 않도록 세션 전체를 비웁니다
    for k in list(st.session_state.keys()):
        del st.session_state[k]


def logout():
    clear_session()
    st.rerun()


# ---------- 화면 ----------
def _render_login():
    st.subheader("🔐 시작하기")
    tab_in, tab_up = st.tabs(["로그인", "처음이에요 (가입)"])

    with tab_in:
        with st.form("login_form"):
            nick = st.text_input("별명")
            pin = st.text_input("PIN (숫자 4~6자리)", type="password")
            submitted = st.form_submit_button("로그인")
        if submitted:
            err = _login(nick, pin)
            if err:
                st.error(err)
            else:
                st.rerun()

    with tab_up:
        st.caption(
            "이 로그인은 시범용 간이 방식이에요. "
            "은행 비밀번호 같은 중요한 숫자는 PIN으로 쓰지 마세요. "
            "PIN을 잊으면 운영자가 계정을 지워야 해요."
        )
        with st.form("signup_form"):
            nick = st.text_input("별명 (2~20자)")
            pin = st.text_input("PIN (숫자 4~6자리)", type="password")
            pin2 = st.text_input("PIN 한 번 더", type="password")
            code = st.text_input("초대 코드", type="password")
            submitted = st.form_submit_button("가입하기")
        if submitted:
            err = _signup(nick, pin, pin2, code)
            if err:
                st.error(err)
            else:
                _login(nick, pin)
                st.rerun()


def require_login():
    """로그인 상태면 True. 아니면 로그인 화면을 보여주고 False."""
    if current_user():
        with st.sidebar:
            st.write(f"👤 {current_user()}")
            if st.button("로그아웃"):
                logout()
        return True
    _render_login()
    return False