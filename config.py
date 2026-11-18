"""설정값 모음. 값을 바꾸고 싶으면 여기만 고치세요."""

DATA_DIR = "data"            # 내 일기가 저장되는 폴더
SAMPLE_DIR = "data_sample"   # 가짜 샘플 폴더
EMOTIONS = ["기쁨", "평온", "불안", "슬픔", "분노", "피로"]
USERS_DIR = f"{DATA_DIR}/users"               # 사용자별 일기 폴더
ACCOUNTS_FILE = f"{DATA_DIR}/_accounts.json"  # 별명과 PIN 해시