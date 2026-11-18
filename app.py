"""앱의 입구. 키를 준비하고, 로그인과 동의를 확인한 뒤 화면을 조립합니다."""


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

# 설정이 확인된 뒤에 나머지를 불러옵니다 (키가 없으면 불러오다가 오류가 나요)
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