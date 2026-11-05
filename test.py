import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

for attempt in range(5):
    try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents="안녕하세요 당신을 한 문장으로 자기소개 해주세요.",
        )
        print(response.text)
        break
    except Exception as e:
        print(f"{attempt + 1}번째 시도 실패: {e}")
        time.sleep(10)
else:
    print("5번 모두 실패했어요. 잠시 후 다시 해보세요.")