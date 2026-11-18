import json
import os
import time
from datetime import date

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# 모델 하나당 한 번 요청에 최대 30초까지만 기다립니다 (단위: 밀리초)
client = genai.Client(http_options=types.HttpOptions(timeout=30000))

# 가장 먼저 시도할 모델 (바뀌면 여기만 고치세요)
PREFERRED = ["gemini-3.6-flash"]

SKIP = ["image", "tts", "live", "embedding", "audio", "veo", "imagen", "robotics"]


def build_models():
    """내 키로 쓸 수 있는 flash 모델을 찾아 시도 순서대로 돌려줍니다."""
    found = []
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "flash" in name and "generateContent" in actions:
                if not any(s in name for s in SKIP):
                    found.append(name)
    except Exception as e:
        print(f"모델 목록을 못 가져왔어요: {str(e)[:80]}")

    found.sort(key=lambda n: "lite" not in n)  # lite를 앞으로
    ordered = list(PREFERRED)
    for n in found:
        if n not in ordered:
            ordered.append(n)
    return ordered


MODELS = build_models()

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
        for attempt in range(3):
            try:
                print(f"[{model}] 시도 {attempt + 1}...", flush=True)
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
            except json.JSONDecodeError:
                print("  형식 오류, 다시 시도해요.", flush=True)
            except Exception as e:
                code = getattr(e, "code", None)
                print(f"  실패 (코드 {code}): {str(e)[:60]}", flush=True)
                if code in (400, 403, 404, 429):
                    break  # 이 모델은 지금 못 쓰니 바로 다음 모델로
                time.sleep(3 * (attempt + 1))  # 503이면 3, 6, 9초 쉬고 재시도
    return None


if __name__ == "__main__":
    print("사용할 모델 순서:", MODELS, flush=True)

    # 테스트용 가짜 일기입니다. 실제 일기가 아니에요.
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