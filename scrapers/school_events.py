"""
school_events.py
京都府 私立高校受験情報 + 学校説明会・オープンキャンパス情報スクレイパー

収集対象:
  - 京都府私立高校一覧（偏差値・倍率）
  - 学校説明会・オープンキャンパス日程
"""

import json
import time
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────
# 1. みんなの高校情報 — 京都府私立高校一覧
# ──────────────────────────────────────────────
MINKOU_PRIVATE_URL = "https://www.minkou.jp/hischool/search/pref_id=26/public=2/"

def scrape_minkou_private():
    """みんなの高校情報から京都府私立高校の基本情報を収集"""
    schools = []
    page = 1

    while True:
        url = MINKOU_PRIVATE_URL if page == 1 else f"{MINKOU_PRIVATE_URL}page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            items = soup.select("li.mod-listSearch-list")
            if not items:
                break

            for item in items:
                name_tag = item.select_one(".mod-listSearch-name > a")
                if not name_tag:
                    continue

                name = name_tag.get_text(strip=True)
                detail_url = "https://www.minkou.jp" + name_tag.get("href", "")

                hensachi_tag = item.select_one(".mod-listSearch-devi dd a")
                hensachi = hensachi_tag.get_text(strip=True) if hensachi_tag else "—"

                area_tag = item.select_one(".mod-listSearch-name span")
                area = area_tag.get_text(strip=True) if area_tag else "—"

                schools.append({
                    "name": name,
                    "hensachi": hensachi,
                    "area": area,
                    "url": detail_url,
                    "type": "私立",
                })

            next_href = f"/hischool/search/pref_id=26/public=2/page={page + 1}"
            if not soup.find("a", href=next_href):
                break

            page += 1
            time.sleep(2)

        except Exception as e:
            print(f"[school_events] 私立高校一覧 取得エラー (page={page}): {e}")
            break

    return schools


# ──────────────────────────────────────────────
# 2. 主要私立高校の説明会情報（直接取得）
# ──────────────────────────────────────────────

# 主要校の公式サイト説明会ページ
MAJOR_SCHOOLS = [
    {
        "name": "洛南高校",
        "official_url": "https://www.rakunan-h.ed.jp/",
        "events_url": "https://www.rakunan-h.ed.jp/",
    },
    {
        "name": "立命館高校",
        "official_url": "https://www.ritsumei.ac.jp/hs/",
        "events_url": "https://www.ritsumei.ac.jp/hs/",
    },
    {
        "name": "同志社高校",
        "official_url": "https://www.doshisha.ed.jp/high/",
        "events_url": "https://www.doshisha.ed.jp/high/",
    },
    {
        "name": "京都女子高校",
        "official_url": "https://www.kyoto-wu.ac.jp/joshi-h/",
        "events_url": "https://www.kyoto-wu.ac.jp/joshi-h/",
    },
    {
        "name": "花園高校",
        "official_url": "https://www.hanazono.ac.jp/hs/",
        "events_url": "https://www.hanazono.ac.jp/hs/",
    },
]

def scrape_school_events_page(school: dict) -> list:
    """個別校の公式サイトから説明会情報を取得"""
    events = []
    try:
        resp = requests.get(school["events_url"], headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # 日付パターン（例: 2026年5月3日、5/3、5月3日）
        date_pattern = re.compile(
            r"(?:\d{4}年)?\d{1,2}月\d{1,2}日|"
            r"\d{1,2}/\d{1,2}"
        )

        # 説明会・オープンキャンパスを含むテキストブロックを探す
        event_keywords = ["説明会", "オープンキャンパス", "見学会", "体験", "入試相談"]

        for tag in soup.find_all(["li", "p", "tr", "div"]):
            text = tag.get_text(strip=True)
            if any(kw in text for kw in event_keywords) and date_pattern.search(text):
                # 100文字以内の短い情報に絞る
                if len(text) < 200:
                    events.append({
                        "school": school["name"],
                        "text": text[:150],
                        "source": school["official_url"],
                    })

        time.sleep(2)

    except Exception as e:
        print(f"[school_events] {school['name']} 取得エラー: {e}")

    return events[:5]  # 最大5件/校


# ──────────────────────────────────────────────
# 3. みんなの高校情報 — 説明会カレンダー（京都）
# ──────────────────────────────────────────────
MINKOU_EVENTS_URL = "https://www.minkou.jp/hischool/opencampus/pref_id=26/"

def scrape_minkou_events():
    """みんなの高校情報のオープンキャンパスカレンダーから京都の情報を収集"""
    events = []
    try:
        resp = requests.get(MINKOU_EVENTS_URL, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # イベントリスト
        items = soup.select(".ocList li, .event-list li, .opencampus-list li")
        for item in items:
            date_tag = item.select_one(".date, .event-date, time")
            name_tag = item.select_one(".schoolName, .school-name, h3, h4")
            event_tag = item.select_one(".eventName, .event-name, .title")

            if not name_tag:
                continue

            events.append({
                "date": date_tag.get_text(strip=True) if date_tag else "日程未定",
                "school": name_tag.get_text(strip=True),
                "event": event_tag.get_text(strip=True) if event_tag else "説明会・OC",
            })

    except Exception as e:
        print(f"[school_events] みんなの高校情報 OC 取得エラー: {e}")

    return events


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────
def main():
    print("[school_events] 収集開始...")

    # 私立高校一覧
    print("  → みんなの高校情報 私立高校一覧...")
    private_schools = scrape_minkou_private()
    print(f"     {len(private_schools)} 校を取得")

    # 説明会カレンダー（みんなの高校情報）
    print("  → みんなの高校情報 説明会カレンダー...")
    calendar_events = scrape_minkou_events()
    print(f"     {len(calendar_events)} 件を取得")

    # 主要校の説明会情報
    print("  → 主要校 公式サイト 説明会情報...")
    official_events = []
    for school in MAJOR_SCHOOLS:
        events = scrape_school_events_page(school)
        official_events.extend(events)
        print(f"     {school['name']}: {len(events)} 件")

    result = {
        "updated_at": datetime.now().isoformat(),
        "private_schools": private_schools,
        "events": {
            "calendar": calendar_events,
            "official": official_events,
        },
    }

    out_path = DATA_DIR / "school_events.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[school_events] 完了 → {out_path}")
    return result


if __name__ == "__main__":
    main()
