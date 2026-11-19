"""일기 내용을 암호화하고 복호화합니다."""

import json
import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


def _fernet():
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("ENCRYPTION_KEY가 설정되지 않았어요.")
    return Fernet(key.encode("utf-8"))


def encrypt_dict(data):
    """딕셔너리를 암호화된 바이트로 바꿉니다."""
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw)


def decrypt_dict(token):
    """암호화된 바이트를 다시 딕셔너리로 되돌립니다."""
    raw = _fernet().decrypt(token)
    return json.loads(raw.decode("utf-8"))