import json
import os
from datetime import date, timedelta

# 일주일치 가짜 분석 결과 (실제 일기가 아닙니다)
DAYS = [
    ({"기쁨": 3, "평온": 4, "불안": 4, "슬픔": 1, "분노": 0, "피로": 5},
     ["복학", "계획"], "복학 준비를 시작하며 약간의 긴장이 느껴지는 하루로 보여요."),
    ({"기쁨": 2, "평온": 3, "불안": 5, "슬픔": 2, "분노": 1, "피로": 6},
     ["수강신청", "수면"], "수강신청 걱정으로 마음이 무거웠던 하루로 보여요."),
    ({"기쁨": 2, "평온": 2, "불안": 7, "슬픔": 2, "분노": 2, "피로": 7},
     ["수강신청", "조급함"], "일정이 쫓기며 불안과 피로가 가장 컸던 날로 보여요."),
    ({"기쁨": 1, "평온": 2, "불안": 6, "슬픔": 4, "분노": 1, "피로": 8},
     ["불면", "피곤"], "잠을 못 자 지치고 기분이 가라앉은 하루로 보여요."),
    ({"기쁨": 4, "평온": 4, "불안": 4, "슬픔": 2, "분노": 0, "피로": 6},
     ["친구", "운동"], "친구와 운동하며 숨통이 트인 하루로 보여요."),
    ({"기쁨": 7, "평온": 6, "불안": 3, "슬픔": 1, "분노": 0, "피로": 4},
     ["가족", "산책"], "가족과 산책하며 기분이 한결 나아진 하루로 보여요."),
    ({"기쁨": 6, "평온": 7, "불안": 3, "슬픔": 1, "분노": 0, "피로": 3},
     ["휴식", "정리"], "차분히 쉬며 한 주를 정리한 하루로 보여요."),
]

os.makedirs("data_sample", exist_ok=True)
today = date.today()

for i, (emotions, keywords, summary) in enumerate(DAYS):
    d = (today - timedelta(days=6 - i)).isoformat()
    entry = {
        "date": d,
        "emotions": emotions,
        "keywords": keywords,
        "summary": summary,
        "text": "(샘플 데이터)",
        "model": "sample",
    }
    with open(f"data_sample/{d}.json", "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)

print("data_sample 폴더에 7개 파일을 만들었어요.")