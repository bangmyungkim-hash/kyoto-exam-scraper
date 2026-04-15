"""
public_exam.py
京都府公立高校 入試情報スクレイパー

収集対象:
  - 入試日程（京都府教育委員会）
  - 学校別 偏差値・倍率（みんなの高校情報）
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
# 1. みんなの高校情報 — 京都府公立高校一覧
# ──────────────────────────────────────────────
MINKOU_URL = "https://www.minkou.jp/hischool/search/pref_id=26/public=1/"

def scrape_minkou_public():
    """みんなの高校情報から京都府公立高校の偏差値・倍率を収集"""
    schools = []
    page = 1

    while True:
        url = MINKOU_URL if page == 1 else f"{MINKOU_URL}page={page}"
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

                # 偏差値
                hensachi_tag = item.select_one(".mod-listSearch-devi dd a")
                hensachi = hensachi_tag.get_text(strip=True) if hensachi_tag else "—"

                # 所在地
                area_tag = item.select_one(".mod-listSearch-name span")
                area = area_tag.get_text(strip=True) if area_tag else "—"

                schools.append({
                    "name": name,
                    "hensachi": hensachi,
                    "area": area,
                    "url": detail_url,
                })

            # 次ページ確認
            next_href = f"/hischool/search/pref_id=26/public=1/page={page + 1}"
            if not soup.find("a", href=next_href):
                break

            page += 1
            time.sleep(2)  # サーバー負荷軽減

        except Exception as e:
            print(f"[public_exam] みんなの高校情報 取得エラー (page={page}): {e}")
            break

    return schools


# ──────────────────────────────────────────────
# 2. みんなの高校情報 — 個別校の倍率を取得
# ──────────────────────────────────────────────
def scrape_school_detail(school: dict) -> dict:
    """個別校ページから最新の倍率を取得"""
    try:
        resp = requests.get(school["url"], headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 倍率テーブル（みんなの高校情報の構造に合わせて調整）
        bairitsu_data = []
        table = soup.select_one("table.examRatio, .exam-ratio-table")
        if table:
            rows = table.select("tr")[1:]  # ヘッダー除く
            for row in rows[:3]:  # 直近3年
                cols = [td.get_text(strip=True) for td in row.select("td")]
                if len(cols) >= 3:
                    bairitsu_data.append({
                        "year": cols[0],
                        "applicants": cols[1],
                        "ratio": cols[2],
                    })

        school["bairitsu"] = bairitsu_data
        time.sleep(1.5)
    except Exception as e:
        print(f"[public_exam] 詳細取得エラー ({school['name']}): {e}")
        school["bairitsu"] = []

    return school


# ──────────────────────────────────────────────
# 3. フォールバック — 固定の入試日程データ
#    ※公式サイト構造変更に備えた安全網
# ──────────────────────────────────────────────
FALLBACK_SCHEDULE = {
    "year": "2027",
    "source": "手動更新（要確認）",
    "schedule": [
        {"event": "出願期間（前期）", "date": "2027年2月上旬"},
        {"event": "学力検査（前期）", "date": "2027年2月中旬"},
        {"event": "合格発表（前期）", "date": "2027年3月上旬"},
        {"event": "出願期間（中期）", "date": "2027年3月上旬"},
        {"event": "学力検査（中期）", "date": "2027年3月中旬"},
        {"event": "合格発表（中期）", "date": "2027年3月下旬"},
    ],
    "official_url": "https://www.kyoto-be.ne.jp/ed-top/",
    "note": "正確な日程は京都府教育委員会の公式サイトでご確認ください。",
}


# ──────────────────────────────────────────────
# 4. 京都府教育委員会 — 入試日程ページ
# ──────────────────────────────────────────────
KYOTO_EDU_URL = "https://www.kyoto-be.ne.jp/ed-top/"

def scrape_kyoto_edu_schedule():
    """京都府教育委員会サイトから入試日程を取得（取得できない場合はフォールバック使用）"""
    try:
        resp = requests.get(KYOTO_EDU_URL, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # 高校入試関連リンクを探す
        exam_links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if re.search(r"高校|入試|選抜", text):
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.kyoto-be.ne.jp" + href
                exam_links.append({"text": text, "url": href})

        if exam_links:
            return {
                "source": "京都府教育委員会",
                "retrieved_at": datetime.now().isoformat(),
                "links": exam_links[:10],
                "official_url": KYOTO_EDU_URL,
            }

    except Exception as e:
        print(f"[public_exam] 京都府教育委員会 取得エラー: {e}")

    # フォールバック
    return {
        **FALLBACK_SCHEDULE,
        "retrieved_at": datetime.now().isoformat(),
        "fallback": True,
    }


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────
def main():
    print("[public_exam] 収集開始...")

    # 入試日程
    print("  → 京都府教育委員会 入試日程...")
    schedule = scrape_kyoto_edu_schedule()

    # 公立高校一覧（偏差値）
    print("  → みんなの高校情報 公立高校一覧...")
    schools = scrape_minkou_public()
    print(f"     {len(schools)} 校を取得")

    # 上位20校の詳細（倍率）取得
    if schools:
        print("  → 詳細情報（倍率）取得中...")
        for i, school in enumerate(schools[:20]):
            schools[i] = scrape_school_detail(school)
            print(f"     [{i+1}/20] {school['name']}")

    result = {
        "updated_at": datetime.now().isoformat(),
        "schedule": schedule,
        "schools": schools,
    }

    out_path = DATA_DIR / "public_exam.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[public_exam] 完了 → {out_path}")
    return result


if __name__ == "__main__":
    main()
