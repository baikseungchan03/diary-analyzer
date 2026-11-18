"""키와 설정값을 준비합니다.
내 컴퓨터에서는 .env 파일을, 배포 환경에서는 Streamlit Secrets를 읽어요."""

import os

from dotenv import load_dotenv

# 앱이 돌아가려면 꼭 필요한 설정값 이름
REQUIRED = ["GEMINI_API_KEY", "INVITE_CODE"]


def load():
    load_dotenv()  # 내 컴퓨터: .env 파일 (이미 있는 값은 덮어쓰지 않아요)
    try:
        import streamlit as st

        for name in REQUIRED:
            if not os.getenv(name) and name in st.secrets:
                os.environ[name] = str(st.secrets[name])
    except Exception:
        pass  # Secrets가 없는 환경(내 컴퓨터 등)에서는 조용히 넘어갑니다


def missing_settings():
    """아직 설정되지 않은 값의 이름 목록을 돌려줍니다."""
    load()
    return [name for name in REQUIRED if not os.getenv(name)]


load()