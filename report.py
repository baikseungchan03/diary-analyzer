"""분석된 일기들을 모아 AI 주간 리포트를 만듭니다."""

import time

from google.genai import types

from analyze import MODELS, client

REPORT_PROMPT = """너는 일주일치 일기 분석 결과를 보고 회고를 도와주는 도우미야.
의학적 진단은 하지 않고, 단정하지 말고 "~로 보여요"처럼 조심스럽게 말해.
다음 순서로 5~7문장으로 써줘.
1) 한 주의 감정 흐름 2) 반복된 주제나 스트레스 요인 3) 좋았던 점
4) 다음 주에 해볼 만한 작은 제안 1~2개
마지막에 힘든 상태가 이어지면 주변 사람이나 전문가와 이야기해보는 것도 방법이라고 한 문장 덧붙여."""


def weekly_report(entries):
    """주간 리포트 글을 돌려줍니다. 실패하면 None."""
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