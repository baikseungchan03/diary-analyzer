"""일기 파일을 읽고 쓰는 일만 합니다."""

import glob
import json
import os

from config import DATA_DIR


def load_entries(folder=DATA_DIR):
    """폴더 안의 모든 일기를 날짜순으로 읽어옵니다."""
    entries = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path, encoding="utf-8") as f:
            entries.append(json.load(f))
    return entries


def load_entry(date_str, folder=DATA_DIR):
    """특정 날짜의 일기 하나를 읽어옵니다. 없으면 None."""
    path = os.path.join(folder, f"{date_str}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_entry(entry, folder=DATA_DIR):
    """일기 하나를 날짜 이름의 파일로 저장합니다. 같은 날짜면 덮어써요."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{entry['date']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)


def has_analysis(entry):
    """AI 분석이 끝난 일기인지 알려줍니다."""
    return bool(entry.get("emotions"))