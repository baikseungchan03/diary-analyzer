"""'주간 회고' 탭 화면."""

from collections import Counter

import pandas as pd
import streamlit as st

from config import DATA_DIR, EMOTIONS, SAMPLE_DIR
from report import weekly_report
from storage import has_analysis, load_entries


def _choose_entries():
    """데이터 폴더와 범위를 고르게 하고, 분석된 일기 목록을 돌려줍니다."""
    has_real = any(has_analysis(e) for e in load_entries(DATA_DIR))
    folder = st.selectbox(
        "데이터 폴더",
        [DATA_DIR, SAMPLE_DIR],
        index=0 if has_real else 1,
    )
    entries = [e for e in load_entries(folder) if has_analysis(e)]

    if not entries:
        st.warning(f"'{folder}' 폴더에 분석된 일기가 없어요.")
        return []

    scope = st.radio("범위", ["최근 7개", "전체"], horizontal=True)
    return entries[-7:] if scope == "최근 7개" else entries


def _to_dataframe(entries):
    df = pd.DataFrame([{"date": e["date"], **e["emotions"]} for e in entries])
    return df.set_index("date").reindex(columns=EMOTIONS).fillna(0)


def _show_metrics(df):
    avg = df.mean()
    col1, col2 = st.columns(2)
    col1.metric("가장 높았던 감정 (평균)", f"{avg.idxmax()} {avg.max():.1f}점")
    col2.metric("가장 불안했던 날", df["불안"].idxmax())


def _show_charts(df, entries):
    st.subheader("감정 변화")
    st.line_chart(df)

    st.subheader("자주 나온 키워드")
    counter = Counter(k for e in entries for k in e.get("keywords", []))
    kw = pd.DataFrame(counter.most_common(10), columns=["키워드", "횟수"])
    st.bar_chart(kw.set_index("키워드"))


def _show_summaries(entries):
    st.subheader("하루하루 요약")
    for e in entries:
        st.write(f"**{e['date']}** · {e['summary']}")


def _show_report(entries):
    st.subheader("AI 주간 리포트")
    if st.button("리포트 생성"):
        with st.spinner("AI가 일주일을 돌아보는 중이에요..."):
            report = weekly_report(entries)
        if report:
            st.write(report)
        else:
            st.error("AI 서버가 붐벼서 실패했어요. 잠시 후 다시 눌러보세요.")


def render():
    entries = _choose_entries()
    if not entries:
        return

    df = _to_dataframe(entries)
    _show_metrics(df)
    _show_charts(df, entries)
    _show_summaries(entries)
    _show_report(entries)