"""'일기 쓰기' 탭 화면."""

import pandas as pd
import streamlit as st

from analyze import analyze_diary
from auth import current_user, current_user_dir
from config import MOOD_KEYS
from storage import has_analysis, load_entries, load_entry, save_entry
from usage import refund, remaining, today_kst, try_use

PRIVACY_NOTICE = (
    "⚠️ 일기 내용은 분석을 위해 구글 서버로 전송돼요. "
    "무료 구간은 입력 내용이 학습에 쓰일 수 있으니, "
    "지금은 민감한 내용을 적지 마세요."
)


def _show_result(entry):
    st.write(f"**요약:** {entry['summary']}")
    st.write("**키워드:** " + ", ".join(entry["keywords"]))
    st.bar_chart(pd.Series(entry["emotions"]))


def _ask_my_mood(suffix, existing):
    """AI 결과를 보기 전에 내 기분을 먼저 점수로 적게 합니다. 안 쓰면 None."""
    saved = (existing or {}).get("my_mood", {})
    use = st.checkbox(
        "내 기분 점수도 기록하기 (AI 결과와 비교할 수 있어요)",
        value=bool(saved),
        key=f"use_mood_{suffix}",
    )
    if not use:
        return None

    st.caption("0~10점. AI 결과를 보기 전에 먼저 적어야 비교가 정확해요.")
    mood = {}
    cols = st.columns(len(MOOD_KEYS))
    for col, k in zip(cols, MOOD_KEYS):
        mood[k] = col.slider(k, 0, 10, saved.get(k, 0), key=f"mood_{k}_{suffix}")
    return mood


def _save_and_analyze(folder, date_str, text, my_mood):
    """일기를 먼저 저장하고, 횟수가 남아 있으면 분석합니다."""
    text = text.strip()
    if not text:
        st.warning("일기를 먼저 적어주세요.")
        return

    entry = {"date": date_str, "text": text}
    if my_mood:
        entry["my_mood"] = my_mood
    save_entry(entry, folder)  # 분석 전에 먼저 저장: 한도가 차도 일기는 남아요

    user = current_user()
    ok, msg = try_use(user, "analyze")
    if not ok:
        st.warning(
            f"일기는 저장됐어요. {msg} "
            "내일 아래의 '다시 분석' 버튼으로 분석할 수 있어요."
        )
        return

    with st.spinner("분석 중이에요. 서버가 붐비면 1분 가까이 걸릴 수 있어요."):
        result = analyze_diary(text)

    if result:
        entry.update(result)
        save_entry(entry, folder)
        st.success("저장하고 분석까지 끝났어요.")
        _show_result(entry)
    else:
        refunded = refund(user, "analyze")
        extra = " 분석 횟수는 돌려드렸어요." if refunded else ""
        st.warning(
            "일기는 저장됐지만 분석은 실패했어요." + extra
            + " 아래의 '다시 분석' 버튼을 나중에 눌러보세요."
        )


def _render_pending(folder):
    """분석이 안 된 일기를 다시 분석하는 버튼."""
    pending = [e for e in load_entries(folder) if not has_analysis(e)]
    if not pending:
        return

    user = current_user()
    st.divider()
    st.write(f"분석이 안 된 일기가 {len(pending)}개 있어요.")
    if st.button("미분석 일기 다시 분석"):
        done = 0
        with st.spinner("다시 분석 중이에요..."):
            for e in pending:
                ok, msg = try_use(user, "analyze")
                if not ok:
                    st.warning(msg)
                    break
                result = analyze_diary(e["text"])
                if result:
                    e.update(result)
                    save_entry(e, folder)
                    done += 1
                else:
                    refund(user, "analyze")
                    break  # 서버가 막혀 있으면 나머지는 시도하지 않아요
        st.write(f"{done}/{len(pending)}개 분석 성공")


def render():
    folder = current_user_dir()
    st.info(PRIVACY_NOTICE)

    today = today_kst()
    d = st.date_input("날짜", value=today, max_value=today)
    date_str = d.isoformat()
    suffix = f"{current_user()}_{date_str}"
    existing = load_entry(date_str, folder)

    if existing:
        state = "분석 완료" if has_analysis(existing) else "아직 분석 안 됨"
        st.caption(f"이 날짜에 저장된 일기가 있어요. ({state}) 저장하면 덮어써요.")

    text = st.text_area(
        "오늘 하루는 어땠나요?",
        value=existing["text"] if existing else "",
        height=200,
        key=f"text_{suffix}",
    )

    my_mood = _ask_my_mood(suffix, existing)

    slot = st.empty()  # 남은 횟수를 맨 마지막에 채워 넣을 자리
    if st.button("저장하고 분석", type="primary"):
        _save_and_analyze(folder, date_str, text, my_mood)

    _render_pending(folder)

    slot.caption(
        f"오늘 남은 일기 분석 횟수: {remaining(current_user(), 'analyze')}회"
    )