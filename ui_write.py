"""'일기 쓰기' 탭 화면."""

from datetime import date

import pandas as pd
import streamlit as st

from analyze import analyze_diary
from storage import has_analysis, load_entries, load_entry, save_entry

PRIVACY_NOTICE = (
    "⚠️ 일기 내용은 분석을 위해 구글 서버로 전송돼요. "
    "무료 구간은 입력 내용이 학습에 쓰일 수 있으니, "
    "지금은 민감한 내용을 적지 마세요."
)


def _show_result(entry):
    st.write(f"**요약:** {entry['summary']}")
    st.write("**키워드:** " + ", ".join(entry["keywords"]))
    st.bar_chart(pd.Series(entry["emotions"]))


def _save_and_analyze(date_str, text):
    """일기를 먼저 저장하고, 그다음 분석합니다. (분석이 실패해도 일기는 남아요)"""
    text = text.strip()
    if not text:
        st.warning("일기를 먼저 적어주세요.")
        return

    entry = {"date": date_str, "text": text}
    save_entry(entry)

    with st.spinner("분석 중이에요. 서버가 붐비면 1분 가까이 걸릴 수 있어요."):
        result = analyze_diary(text)

    if result:
        entry.update(result)
        save_entry(entry)
        st.success("저장하고 분석까지 끝났어요.")
        _show_result(entry)
    else:
        st.warning(
            "일기는 저장됐지만 분석은 실패했어요. "
            "아래의 '다시 분석' 버튼을 나중에 눌러보세요."
        )


def _render_pending():
    """분석이 안 된 일기를 다시 분석하는 버튼."""
    pending = [e for e in load_entries() if not has_analysis(e)]
    if not pending:
        return

    st.divider()
    st.write(f"분석이 안 된 일기가 {len(pending)}개 있어요.")
    if st.button("미분석 일기 다시 분석"):
        done = 0
        with st.spinner("다시 분석 중이에요..."):
            for e in pending:
                result = analyze_diary(e["text"])
                if result:
                    e.update(result)
                    save_entry(e)
                    done += 1
                else:
                    break  # 서버가 막혀 있으면 나머지는 시도하지 않아요
        st.write(f"{done}/{len(pending)}개 분석 성공")


def render():
    st.info(PRIVACY_NOTICE)

    d = st.date_input("날짜", value=date.today(), max_value=date.today())
    date_str = d.isoformat()
    existing = load_entry(date_str)

    if existing:
        state = "분석 완료" if has_analysis(existing) else "아직 분석 안 됨"
        st.caption(f"이 날짜에 저장된 일기가 있어요. ({state}) 저장하면 덮어써요.")

    text = st.text_area(
        "오늘 하루는 어땠나요?",
        value=existing["text"] if existing else "",
        height=200,
        key=f"text_{date_str}",
    )

    if st.button("저장하고 분석", type="primary"):
        _save_and_analyze(date_str, text)

    _render_pending()