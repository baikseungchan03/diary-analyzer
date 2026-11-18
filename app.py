"""앱의 입구. 화면을 조립만 하고, 실제 일은 각 모듈이 합니다."""

import streamlit as st

import ui_review
import ui_write

st.set_page_config(page_title="주간 감정 회고", page_icon="📓")
st.title("📓 주간 감정 회고")
st.caption("AI의 분석은 참고용이며 의학적 진단이 아닙니다.")

tab_write, tab_review = st.tabs(["✍️ 일기 쓰기", "📊 주간 회고"])
with tab_write:
    ui_write.render()
with tab_review:
    ui_review.render()