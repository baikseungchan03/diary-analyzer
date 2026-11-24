from backend import env_setup  # 가장 먼저: .env 또는 Secrets에서 키를 불러옵니다

import streamlit as st

st.set_page_config(page_title="주간 감정 회고", page_icon="📓")
st.title("📓 주간 감정 회고")
st.caption("AI의 분석은 참고용이며 의학적 진단이 아닙니다.")

missing = env_setup.missing_settings()
if missing:
    st.error("운영자 설정이 빠져 있어요: " + ", ".join(missing))
    st.caption(
        "내 컴퓨터에서는 .env 파일에, 배포한 앱에서는 앱 설정의 Secrets에 "
        "값을 넣어주세요."
    )
    st.stop()

from backend import db  # noqa: E402
db.init_db()                      # ← db연결

import time  # noqa: E402
db.prune_sessions(time.time())  # 기한 지난 로그인 토큰 정리

from backend import auth  # noqa: E402
from frontend import ui_account, ui_review, ui_write  # noqa: E402

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