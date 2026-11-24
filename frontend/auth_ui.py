"""로그인·가입 화면, 사이드바 로그아웃 버튼. 판단 로직은 backend/auth.py에 있어요."""

import streamlit as st

from backend import auth


def render_login():
    st.subheader("🔐 시작하기")
    tab_in, tab_up = st.tabs(["로그인", "처음이에요 (가입)"])

    with tab_in:
        with st.form("login_form"):
            nick = st.text_input("별명")
            pin = st.text_input("PIN (숫자 4~6자리)", type="password")
            submitted = st.form_submit_button("로그인")
        if submitted:
            err = auth.login(nick, pin)
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
            err = auth.signup(nick, pin, pin2, code)
            if err:
                st.error(err)
            else:
                auth.login(nick, pin)
                st.rerun()


def render_sidebar():
    with st.sidebar:
        st.write(f"👤 {auth.current_user()}")
        if st.button("로그아웃"):
            auth.logout()