"""설정값 모음. 값을 바꾸고 싶으면 여기만 고치세요."""

DATA_DIR = "data"            # 데이터 폴더
SAMPLE_DIR = "data_sample"   # 가짜 샘플 폴더
EMOTIONS = ["기쁨", "평온", "불안", "슬픔", "분노", "피로"]

MOOD_KEYS = ["기쁨", "불안", "피로"]   # 내 점수와 AI 점수를 비교할 감정

USERS_DIR = f"{DATA_DIR}/users"               # 사용자별 일기 폴더
ACCOUNTS_FILE = f"{DATA_DIR}/_accounts.json"  # 별명과 PIN 해시

CONSENT_VERSION = 1   # 동의 문구를 바꾸면 이 숫자를 올리세요. 모두에게 다시 동의를 받아요.

USAGE_FILE = f"{DATA_DIR}/_usage.json"   # 오늘 몇 번 썼는지 기록하는 파일

# 사람당 하루 한도
DAILY_LIMITS = {"analyze": 2, "report": 1}
# 모든 사람을 합친 하루 한도 (내 무료 키 보호용)
GLOBAL_DAILY_LIMITS = {"analyze": 20, "report": 10}
# 실패했을 때 횟수를 돌려주는 최대 횟수 (하루, 사람당)
MAX_REFUNDS_PER_DAY = 3

KIND_LABELS = {"analyze": "일기 분석", "report": "주간 리포트"}