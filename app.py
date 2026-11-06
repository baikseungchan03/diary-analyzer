import glob
import json
import os
import time
from collections import Counter
from datetime import date

import pandas as pd
import streamlit as st
from google.genai import types

from analyze import MODELS, analyze_diary, client

DATA_DIR = "data"
EMOTIONS = ["기쁨", "평온", "불안", "슬픔", "분노", "피로"]

REPORT_PROMPT = """너는 일주일치 일기 분석 결과를 보고 회고를 도와주는 도우미야.
의학적 진단은 하지 않고, 단정하지 말고 "~로 보여요"처럼 조심스럽게 말해.
다음 순서로 5~7문장으로 써줘.
1) 한 주의 감정 흐름 2) 반복된 주제나 스트레스 요인 3) 좋았던 점
4) 다음 주에 해볼 만한 작은 제안 1~2개
마지막에 힘든 상태가 이어지면 주변 사람이나 전문가와 이야기해보는 것도 방법이라고 한 문장 덧붙여."""


# ---------- 파일 읽기/쓰기 ----------
def load_entries(folder):
    entries = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path, encoding="utf-8") as f:
            entries.append(json.load(f))
    return entries


def load_entry(folder, d):
    path = os.path.join(folder, f"{d}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_entry(entry):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{entry['date']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)


# ---------- 주간 리포트 ----------
def weekly_report(entries):
    lines = "\n".join(
        f"- {e['date']}: 감정 {e['emotions']}, 키워드 {e['keywords']}, 요약 {e['summary']}"
        for e in entries
    )
    for model in MODELS:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=f"일주일치 분석 결과:\n{lines}",
                    config=types.GenerateContentConfig(
                        system_instruction=REPORT_PROMPT
                    ),
                )
                return response.text
            except Exception as e:
                code = getattr(e, "code", None)
                print(f"[리포트/{model}] 실패 (코드 {code})", flush=True)
                if code in (400, 403, 404, 429):
                    break  # 이 모델은 지금 못 쓰니 다음 모델로
                time.sleep(3 * (attempt + 1))
    return None


# ---------- 일기 쓰기 탭 ----------
def show_result(entry):
    st.write(f"**요약:** {entry['summary']}")
    st.write("**키워드:** " + ", ".join(entry["keywords"]))
    st.bar_chart(pd.Series(entry["emotions"]))


def render_write():
    st.info(
        "⚠️ 일기 내용은 분석을 위해 구글 서버로 전송돼요. "
        "무료 구간은 입력 내용이 학습에 쓰일 수 있으니, "
        "지금은 민감한 내용을 적지 마세요."
    )

    d = st.date_input("날짜", value=date.today(), max_value=date.today())
    d_str = d.isoformat()
    existing = load_entry(DATA_DIR, d_str)

    if existing:
        state = "분석 완료" if existing.get("emotions") else "아직 분석 안 됨"
        st.caption(f"이 날짜에 저장된 일기가 있어요. ({state}) 저장하면 덮어써요.")

    text = st.text_area(
        "오늘 하루는 어땠나요?",
        value=existing["text"] if existing else "",
        height=200,
        key=f"text_{d_str}",
    )

    if st.button("저장하고 분석", type="primary"):
        text = text.strip()
        if not text:
            st.warning("일기를 먼저 적어주세요.")
        else:
            entry = {"date": d_str, "text": text}
            save_entry(entry)  # 분석 전에 먼저 저장
            with st.spinner("분석 중이에요. 서버가 붐비면 1분 가까이 걸릴 수 있어요."):
                result = analyze_diary(text)
            if result:
                entry.update(result)
                save_entry(entry)
                st.success("저장하고 분석까지 끝났어요.")
                show_result(entry)
            else:
                st.warning(
                    "일기는 저장됐지만 분석은 실패했어요. "
                    "아래의 '다시 분석' 버튼을 나중에 눌러보세요."
                )

    # 분석 안 된 일기 다시 분석
    pending = [e for e in load_entries(DATA_DIR) if not e.get("emotions")]
    if pending:
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
                        break
            st.write(f"{done}/{len(pending)}개 분석 성공")


# ---------- 주간 회고 탭 ----------
def render_review():
    has_real = any(e.get("emotions") for e in load_entries(DATA_DIR))
    folder = st.selectbox(
        "데이터 폴더",
        ["data", "data_sample"],
        index=0 if has_real else 1,
    )
    entries = [e for e in load_entries(folder) if e.get("emotions")]

    if not entries:
        st.warning(f"'{folder}' 폴더에 분석된 일기가 없어요.")
        return

    scope = st.radio("범위", ["최근 7개", "전체"], horizontal=True)
    if scope == "최근 7개":
        entries = entries[-7:]

    df = pd.DataFrame([{"date": e["date"], **e["emotions"]} for e in entries])
    df = df.set_index("date").reindex(columns=EMOTIONS).fillna(0)

    avg = df.mean()
    col1, col2 = st.columns(2)
    col1.metric("가장 높았던 감정 (평균)", f"{avg.idxmax()} {avg.max():.1f}점")
    col2.metric("가장 불안했던 날", df["불안"].idxmax())

    st.subheader("감정 변화")
    st.line_chart(df)

    st.subheader("자주 나온 키워드")
    counter = Counter(k for e in entries for k in e.get("keywords", []))
    kw = pd.DataFrame(counter.most_common(10), columns=["키워드", "횟수"])
    st.bar_chart(kw.set_index("키워드"))

    st.subheader("하루하루 요약")
    for e in entries:
        st.write(f"**{e['date']}** · {e['summary']}")

    st.subheader("AI 주간 리포트")
    if st.button("리포트 생성"):
        with st.spinner("AI가 일주일을 돌아보는 중이에요..."):
            report = weekly_report(entries)
        if report:
            st.write(report)
        else:
            st.error("AI 서버가 붐벼서 실패했어요. 잠시 후 다시 눌러보세요.")


# ---------- 화면 ----------
st.set_page_config(page_title="주간 감정 회고", page_icon="📓")
st.title("📓 주간 감정 회고")
st.caption("AI의 분석은 참고용이며 의학적 진단이 아닙니다.")

tab_write, tab_review = st.tabs(["✍️ 일기 쓰기", "📊 주간 회고"])
with tab_write:
    render_write()
with tab_review:
    render_review()