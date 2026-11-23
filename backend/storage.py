"""일기를 암호화된 DB에 저장하고 읽습니다. (샘플 데이터만 예외로 파일을 읽어요)"""

import csv
import glob
import io
import json
import os
import re

from . import db
from .config import EMOTIONS, MOOD_KEYS

# 별명: 2~20자, 한글/영문/숫자로 시작, 중간에 _ - 허용
NICKNAME_RULE = re.compile(r"[A-Za-z0-9가-힣][A-Za-z0-9가-힣_-]{1,19}")


def is_valid_nickname(name):
    return bool(NICKNAME_RULE.fullmatch(name or ""))


def _check(nickname):
    if not is_valid_nickname(nickname):
        raise ValueError("올바르지 않은 별명")


def load_sample_entries(folder):
    """샘플 데이터(가짜 일기)만 파일에서 읽어옵니다."""
    entries = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path, encoding="utf-8") as f:
            entries.append(json.load(f))
    return entries


def load_entries(nickname):
    """한 사람의 모든 일기를 DB에서 읽어옵니다."""
    _check(nickname)
    return db.load_entries(nickname)


def load_entry(date_str, nickname):
    """특정 날짜의 일기 하나를 읽어옵니다. 없으면 None."""
    _check(nickname)
    return db.load_entry(nickname, date_str)


def save_entry(entry, nickname):
    """일기 하나를 저장합니다. 같은 날짜면 덮어써요."""
    _check(nickname)
    db.save_entry(nickname, entry)


def has_analysis(entry):
    """AI 분석이 끝난 일기인지 알려줍니다."""
    return bool(entry.get("emotions"))


def delete_user_files(nickname):
    """한 사람의 일기를 DB에서 전부 지웁니다. 지웠으면 True."""
    _check(nickname)
    return db.delete_entries(nickname)


# ---------- 내려받기 ----------
def export_json(entries):
    """모든 일기를 JSON 글자(바이트)로 만듭니다. 백업용."""
    return json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8")


def export_csv(entries):
    """모든 일기를 CSV로 만듭니다. 엑셀에서 한글이 깨지지 않게 BOM을 붙여요."""
    fields = (
        ["date", "text", "summary", "keywords"]
        + [f"AI_{k}" for k in EMOTIONS]
        + [f"내_{k}" for k in MOOD_KEYS]
    )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for e in entries:
        row = {
            "date": e.get("date", ""),
            "text": e.get("text", ""),
            "summary": e.get("summary", ""),
            "keywords": ", ".join(e.get("keywords", [])),
        }
        for k in EMOTIONS:
            row[f"AI_{k}"] = e.get("emotions", {}).get(k, "")
        for k in MOOD_KEYS:
            row[f"내_{k}"] = e.get("my_mood", {}).get(k, "")
        writer.writerow(row)
    return buf.getvalue().encode("utf-8-sig")