"""앱의 입구. 로그인과 동의를 확인하고, 화면을 조립만 합니다."""

import streamlit as st

import auth
import ui_account
import ui_review
import ui_write

st.set_page_config(page_title="주간 감정 회고", page_icon="📓")
st.title("📓 주간 감정 회고")
st.caption("AI의 분석은 참고용이며 의학적 진단이 아닙니다.")

# 삭제 후 같은 안내 문구를 한 번만 보여줍니다
flash = st.session_state.pop("flash", None)
if flash:
    st.success(flash)

if auth.require_login():
    if not auth.has_consent():
        ui_account.render_consent()
    else:
        tab_write, tab_review, tab_account = st.tabs(
            ["✍️ 일기 쓰기", "📊 주간 회고", "⚙️ 내 정보"]
        )
        with tab_write:
            ui_write.render()
        with tab_review:
            ui_review.render()
        with tab_account:
            ui_account.render_account()