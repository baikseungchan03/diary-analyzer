import json
import os
import time
from datetime import date

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()


MODELS = ["gemini-3.8-flash"]

SYSTEM_PROMPT = """너는 일기를 읽고 감정을 정리해주는 회고 도우미야.
의학적 진단은 하지 않아. 단정하지 말고 "~로 보여요"처럼 조심스럽게 말해.
반드시 아래 JSON 형식으로만 답해. 다른 말은 쓰지 마.

{
  "emotions": {"기쁨": 0, "평온": 0, "불안": 0, "슬픔": 0, "분노": 0, "피로": 0},
  "keywords": ["키워드1", "키워드2"],
  "summary": "한 문장 요약"
}

규칙:
- emotions의 각 값은 0~10 사이 정수야. (0은 전혀 없음, 10은 매우 강함)
- keywords는 최대 5개야.
- summary는 한국어 한 문장이야.
"""


def analyze_diary(text):
    """일기 한 편을 분석해서 딕셔너리로 돌려줍니다. 실패하면 None."""
    for model in MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=text,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                    ),
                )
                result = json.loads(response.text)
                result["model"] = model
                return result
            except Exception as e:
                print(f"{model} {attempt + 1}번째 실패: {str(e)[:100]}")
                time.sleep(5)
    return None


if __name__ == "__main__":
    # 테스트용 가짜 일기
    sample = (
        "오늘은 복학 준비 때문에 도서관에 갔다. 수강신청 일정을 보니 "
        "마음이 조급해졌다. 밤에 잠이 잘 안 와서 많이 피곤했지만, "
        "저녁에 친구를 만나서 오랜만에 크게 웃었다."
    )

    today = date.today().isoformat()
    result = analyze_diary(sample)

    if result is None:
        print("분석에 실패했어요. 잠시 후 다시 해보세요.")
    else:
        result["date"] = today
        result["text"] = sample

        os.makedirs("data", exist_ok=True)
        path = f"data/{today}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"\n저장 완료: {path}")