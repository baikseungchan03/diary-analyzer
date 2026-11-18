"""동의 화면과 '내 정보' 탭 (내려받기, 삭제)."""

import streamlit as st

import auth
from storage import delete_user_files, export_csv, export_json, load_entries

CONSENT_TEXT = """
**시범 사용 안내**

저장되는 것: 별명, PIN(암호화된 값), 일기 본문, AI 분석 결과, 내가 적은 기분 점수

- 쓴 내용은 AI 분석을 위해 **구글 서버로 전송돼요.**
- 무료 구간은 입력 내용이 학습에 쓰일 수 있어서, **민감한 내용은 쓰지 말아주세요.**
- 앱을 만든 운영자는 기술적으로 저장된 내용을 볼 수 있어요. 개인적으로 열어보지 않겠다고 약속해요.
- 시범이 끝나면 모든 데이터를 지워요. 중간에도 **'내 정보' 탭에서 직접** 지울 수 있어요.
- 이 앱에서 지워도, **이미 구글로 전송된 내용은 지울 수 없어요.**
- 오류로 기록이 사라질 수 있어요. 중요한 내용은 **'내 정보' 탭에서 내려받아** 따로 보관하세요.
- 참여는 언제든 그만둘 수 있어요.
"""


def render_consent():
    """처음 한 번 보여주는 동의 화면."""
    st.subheader("📝 시작하기 전에 읽어주세요")
    st.markdown(CONSENT_TEXT)
    agree = st.checkbox("위 내용을 읽었고, 이해하고 동의해요")
    if st.button("동의하고 시작", type="primary", disabled=not agree):
        auth.give_consent()
        st.rerun()
    st.caption("동의하지 않으면 왼쪽 사이드바의 '로그아웃'을 눌러 나가세요.")


def _confirm(pin, sure):
    """삭제 전 확인: 체크박스와 PIN. 통과하면 True."""
    if not sure:
        st.error("체크박스를 먼저 눌러주세요.")
        return False
    err = auth.verify_pin(pin)
    if err:
        st.error(err)
        return False
    return True


def _render_download(entries, nick):
    st.subheader("📥 내 기록 내려받기")
    st.caption("앱이 재시작되면 기록이 사라질 수 있어요. 가끔 내려받아 두세요.")
    if not entries:
        st.info("아직 내려받을 일기가 없어요.")
        return
    c1, c2 = st.columns(2)
    c1.download_button(
        "JSON으로 받기 (백업용)",
        data=export_json(entries),
        file_name=f"{nick}_diary.json",
        mime="application/json",
    )
    c2.download_button(
        "CSV로 받기 (엑셀용)",
        data=export_csv(entries),
        file_name=f"{nick}_diary.csv",
        mime="text/csv",
    )


def _render_delete(nick):
    st.subheader("🗑️ 지우기")
    st.warning(
        "지운 내용은 되돌릴 수 없어요. 먼저 위에서 내려받아 두세요. "
        "이미 구글로 전송된 내용은 이 앱에서 지울 수 없어요."
    )

    with st.expander("내 일기 전체 삭제"):
        with st.form("delete_diaries"):
            pin = st.text_input("PIN 확인", type="password")
            sure = st.checkbox("일기를 전부 지우는 것을 이해했어요")
            go = st.form_submit_button("일기 전체 삭제")
        if go and _confirm(pin, sure):
            delete_user_files(nick)
            st.session_state["flash"] = "내 일기를 모두 삭제했어요."
            st.rerun()

    with st.expander("계정까지 삭제 (탈퇴)"):
        with st.form("delete_account"):
            pin = st.text_input("PIN 확인", type="password", key="pin_del_acc")
            sure = st.checkbox("계정과 일기가 모두 사라지는 것을 이해했어요")
            go = st.form_submit_button("계정 삭제")
        if go and _confirm(pin, sure):
            auth.delete_account()
            st.rerun()


def render_account():
    """'내 정보' 탭."""
    nick = auth.current_user()
    entries = load_entries(auth.current_user_dir())

    st.subheader("⚙️ 내 정보")
    st.write(f"별명: **{nick}**")
    st.write(f"저장된 일기: **{len(entries)}개**")
    when = auth.consent_time()
    if when:
        st.caption(f"동의한 시각: {when}")

    st.divider()
    _render_download(entries, nick)
    st.divider()
    _render_delete(nick)