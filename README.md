# 주간 감정 회고 (Diary Analyzer)

하루 일기를 쓰면 AI가 감정을 분석하고, 일주일치를 모아 감정 흐름과 주간 리포트를 보여주는 개인 프로젝트입니다. 전역 후 AI/정보통신 역량을 다시 쌓기 위해 시작했고, 현재는 소규모(10명 이내) 시범 서비스로 운영 중입니다.

> ⚠️ AI 분석은 참고용이며 의학적 진단이 아닙니다.

## 주요 기능

- 별명 + PIN 로그인 (초대 코드 기반 가입)
- 날짜별 일기 작성과 저장, 일기별 감정 점수·키워드·한 줄 요약 분석
- 내 기분 점수 직접 입력 + AI 점수와 비교하는 그래프
- 감정 변화 그래프, 키워드 빈도 그래프
- AI 주간 리포트 생성
- AI 서버가 막혀도 일기는 먼저 저장되고, 나중에 다시 분석 가능 (모델 자동 탐색 + 재시도)
- 하루 AI 사용 횟수 제한 (사람별 + 전체 합산, 한국 시간 기준)
- 동의 화면, 내 데이터 내려받기(JSON/CSV), 일기·계정 삭제
- 새로고침(F5)해도 로그인이 유지되는 세션 쿠키 (시간 기반 토큰 회전 + 재사용 탐지)
- 일기 본문은 암호화되어 저장

## 기술 스택

Python, Streamlit, pandas, Google Gemini API, MySQL, cryptography(Fernet), PyMySQL

## 저장소 구조

```
diary_analyzer/
├─ app.py                 앱 입구, 로그인·동의 확인, 화면 조립
├─ backend/               화면 없는 로직
│   ├─ config.py          설정값 모음
│   ├─ env_setup.py       .env / Streamlit Secrets에서 키 불러오기
│   ├─ storage.py         일기 읽기/쓰기 (DB 연동 창구)
│   ├─ auth.py            로그인/가입/세션 로직
│   ├─ usage.py           하루 AI 사용 횟수 제한
│   ├─ analyze.py         일기 한 편 AI 분석
│   ├─ report.py          주간 리포트 생성
│   ├─ crypto.py          일기 암호화/복호화
│   └─ db/                MySQL 접근 (기능별로 분리)
│       ├─ connection.py  연결 관리 (재사용)
│       ├─ schema.py      테이블 생성
│       ├─ entries.py     일기 CRUD
│       ├─ accounts.py    계정 CRUD
│       ├─ usage_repo.py  사용량 CRUD
│       └─ sessions.py    로그인 세션 토큰 CRUD
├─ frontend/              Streamlit 화면
│   ├─ auth_ui.py         로그인/가입 화면, 사이드바
│   ├─ ui_write.py        '일기 쓰기' 탭
│   ├─ ui_review.py       '주간 회고' 탭
│   ├─ ui_account.py      동의 화면, '내 정보' 탭
│   └─ cookie_helper.py   브라우저 쿠키 저장/조회
└─ scripts/               독립 실행 도구
    ├─ create_sample.py   샘플 데이터 생성
    ├─ check_models.py    사용 가능한 Gemini 모델 진단
    └─ test.py            API 연결 테스트
```

## 실행 방법

1. 저장소를 내려받습니다.
2. 가상환경을 만들고 켭니다.
3. 라이브러리를 설치합니다.
4. `.env.example`을 복사해 `.env`로 이름을 바꾸고, 아래 값을 채웁니다.
   - `GEMINI_API_KEY`: Google AI Studio에서 발급
   - `INVITE_CODE`: 가입 시 필요한 초대 코드 (직접 정함)
   - `ENCRYPTION_KEY`: 일기 암호화 키 (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`로 생성)
   - `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DB`, `MYSQL_USER`, `MYSQL_PASSWORD`: MySQL 접속 정보
5. 샘플 데이터를 만들고 실행합니다.

## 배포

Streamlit Community Cloud에 배포할 때는 위 `.env` 항목을 앱 설정의 **Secrets**에 TOML 형식(모든 값에 큰따옴표)으로 동일하게 등록합니다. MySQL은 Railway 등 외부 호스팅을 사용해, Streamlit 컨테이너가 재시작되어도 데이터가 유지되도록 합니다.

## 데이터와 보안

- 일기 본문은 `ENCRYPTION_KEY`로 암호화되어 MySQL에 저장됩니다. **이 키를 잃어버리면 기존 일기를 복구할 수 없습니다.**
- PIN은 원문이 아니라 PBKDF2 해시로 저장됩니다.
- 로그인 유지 토큰은 해시로 저장되며, 발급 후 1시간이 지나면 다음 사용 시 자동으로 새 토큰으로 교체됩니다. 교체된 옛 토큰이 다시 사용되면 재사용 공격으로 간주해 해당 계정의 모든 세션을 강제 종료합니다.
- 일기 내용은 분석을 위해 Google Gemini API로 전송됩니다. 무료 구간에서는 입력이 학습에 쓰일 수 있어, 실명·연락처 등 특정 가능한 정보는 입력하지 않도록 안내하고 있습니다. (이 앱의 삭제 기능은 자체 DB에서만 유효하며, 이미 전송된 데이터의 삭제는 보장하지 않습니다.)
- 일기 데이터(`data/`)와 API 키(`.env`)는 `.gitignore`로 저장소에서 제외됩니다.

## 개인정보와 사용량 제한

- 가입 시 동의 화면을 거치며, 동의 문구가 바뀌면 `CONSENT_VERSION`을 올려 재동의를 받습니다.
- '내 정보' 탭에서 본인 데이터 내려받기(JSON/CSV), 일기 전체 삭제, 계정 삭제(탈퇴)가 가능합니다.
- 하루 AI 사용 횟수는 사람별(일기 분석 2회, 리포트 1회)과 전체 합산(분석 20회, 리포트 10회)로 제한됩니다. 분석 실패 시 제한적으로 횟수를 돌려줍니다.

## 겪은 문제와 배운 점

- 모델이 신규 사용자에게 막혀 404가 났고, 오류 메시지의 추천 모델로 해결함
- 서버 과부하(503)에 대비해 모델 자동 탐색·전환과 '저장 먼저, 분석 나중' 구조를 만듦
- Streamlit Community Cloud는 컨테이너 기반이라 재시작 시 로컬 파일이 초기화될 수 있어, SQLite → MySQL(Railway)로 전환함
- 로그인 유지 토큰을 주소창에 노출하던 초기 설계를 보안 점검을 통해 발견하고, 쿠키 기반 + 토큰 해시화 + 시간 기반 회전 + 재사용 탐지로 개선함
- 세션 토큰을 "쓸 때마다 매번 교체"하면 동시 탭·재시도 요청이 충돌해 정상 사용자가 로그아웃될 수 있다는 점을 배우고, 일정 시간 간격을 둔 교체 방식으로 수정함

## 앞으로 할 일

- 시범 참가자 동의 절차 및 안내문 최종본 작성
- 배포된 앱 전체 흐름 최종 리허설 (모바일 포함)
- 데이터 보존 기간·백업·삭제 절차 공식 문서화
