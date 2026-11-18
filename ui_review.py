"""'주간 회고' 탭 화면."""

from collections import Counter

import pandas as pd
import streamlit as st

from auth import current_user, current_user_dir
from config import EMOTIONS, MOOD_KEYS, SAMPLE_DIR
from report import weekly_report
from storage import has_analysis, load_entries
from usage import refund, remaining, try_use


def _choose_entries():
    """데이터와 범위를 고르게 하고, 분석된 일기 목록을 돌려줍니다."""
    mine = current_user_dir()
    has_real = any(has_analysis(e) for e in load_entries(mine))

    options = {"내 기록": mine, "샘플 데이터": SAMPLE_DIR}
    label = st.selectbox("데이터", list(options), index=0 if has_real else 1)
    entries = [e for e in load_entries(options[label]) if has_analysis(e)]

    if not entries:
        st.warning(f"'{label}'에 분석된 일기가 없어요.")
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


def _show_comparison(entries):
    """내가 적은 점수와 AI 점수를 나란히 비교합니다."""
    rated = [e for e in entries if e.get("my_mood")]
    if not rated:
        return

    st.subheader("내 점수 vs AI 점수")
    rows = []
    for e in rated:
        row = {"date": e["date"]}
        for k in MOOD_KEYS:
            row[f"내 {k}"] = e["my_mood"].get(k, 0)
            row[f"AI {k}"] = e["emotions"].get(k, 0)
        rows.append(row)
    cmp_df = pd.DataFrame(rows).set_index("date")
    st.line_chart(cmp_df)

    cols = st.columns(len(MOOD_KEYS))
    for col, k in zip(cols, MOOD_KEYS):
        diff = (cmp_df[f"내 {k}"] - cmp_df[f"AI {k}"]).abs().mean()
        col.metric(f"{k} 평균 차이", f"{diff:.1f}점")
    st.caption("차이가 작을수록 AI 분석이 내 느낌과 가까워요.")


def _show_summaries(entries):
    st.subheader("하루하루 요약")
    for e in entries:
        st.write(f"**{e['date']}** · {e['summary']}")


def _show_report(entries):
    st.subheader("AI 주간 리포트")
    user = current_user()

    slot = st.empty()  # 남은 횟수를 마지막에 채워 넣을 자리
    if st.button("리포트 생성"):
        ok, msg = try_use(user, "report")
        if not ok:
            st.warning(msg)
        else:
            with st.spinner("AI가 일주일을 돌아보는 중이에요..."):
                report = weekly_report(entries)
            if report:
                st.write(report)
            else:
                refunded = refund(user, "report")
                extra = " 횟수는 돌려드렸어요." if refunded else ""
                st.error("AI 서버가 붐벼서 실패했어요. 잠시 후 다시 눌러보세요." + extra)

    slot.caption(f"오늘 남은 리포트 횟수: {remaining(user, 'report')}회")


def render():
    entries = _choose_entries()
    if not entries:
        return

    df = _to_dataframe(entries)
    _show_metrics(df)
    _show_charts(df, entries)
    _show_comparison(entries)
    _show_summaries(entries)
    _show_report(entries)