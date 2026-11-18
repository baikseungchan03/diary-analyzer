import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# 모델 하나당 최대 20초만 기다립니다 (단위: 밀리초)
client = genai.Client(http_options=types.HttpOptions(timeout=20000))

SKIP = ["image", "tts", "live", "embedding", "audio", "veo", "imagen", "robotics"]

print("모델 목록을 가져오는 중...", flush=True)

candidates = []
for m in client.models.list():
    name = m.name.replace("models/", "")
    actions = getattr(m, "supported_actions", None) or []
    if "flash" in name and "generateContent" in actions:
        if not any(s in name for s in SKIP):
            candidates.append(name)

# 가벼운 lite 모델을 먼저 시험합니다
candidates.sort(key=lambda n: "lite" not in n)

print(f"테스트할 모델 {len(candidates)}개\n", flush=True)

ok_models = []
for i, name in enumerate(candidates, 1):
    print(f"[{i}/{len(candidates)}] {name} 시험 중...", flush=True)
    start = time.time()
    try:
        r = client.models.generate_content(
            model=name,
            contents="안녕이라고만 답해줘.",
            config=types.GenerateContentConfig(max_output_tokens=20),
        )
        text = (r.text or "").strip()[:20]
        print(f"   OK    ({time.time() - start:.1f}초) -> {text}", flush=True)
        ok_models.append(name)
    except Exception as e:
        code = getattr(e, "code", "?")
        print(f"   FAIL  (코드 {code}, {time.time() - start:.1f}초)", flush=True)

print("\n===== 결과 =====", flush=True)
if ok_models:
    print("지금 쓸 수 있는 모델:", flush=True)
    for n in ok_models:
        print("  -", n, flush=True)
else:
    print("쓸 수 있는 모델이 없어요. 시간을 두고 다시 해보세요.", flush=True)