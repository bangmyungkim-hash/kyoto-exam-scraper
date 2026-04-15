"""
wp_update.py
収集した京都高校受験情報を WordPress REST API でページ更新

環境変数（GitHub Secrets）:
  WP_URL           例: https://aioijuku.com
  WP_USER          WordPress ユーザー名
  WP_APP_PASSWORD  WordPress アプリケーションパスワード

更新対象ページ（スラッグで管理）:
  kyoto-kouritsu-exam   → 公立高校入試情報
  kyoto-shiritsu-exam   → 私立高校受験情報
  kyoto-school-events   → 説明会・オープンキャンパス
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
WP_URL = os.environ.get("WP_URL", "").rstrip("/")
WP_USER = os.environ.get("WP_USER", "")
WP_APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")

DATA_DIR = Path(__file__).parent.parent / "data"

AUTH = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)
API_BASE = f"{WP_URL}/wp-json/wp/v2"


# ──────────────────────────────────────────────
# WordPress API ユーティリティ
# ──────────────────────────────────────────────
def get_page_by_slug(slug: str) -> dict | None:
    """スラッグでページを検索して返す"""
    resp = requests.get(
        f"{API_BASE}/pages",
        params={"slug": slug, "status": "any"},
        auth=AUTH,
        timeout=15,
    )
    resp.raise_for_status()
    pages = resp.json()
    return pages[0] if pages else None


def create_or_update_page(slug: str, title: str, content: str, excerpt: str = "") -> dict:
    """ページを作成または更新する"""
    existing = get_page_by_slug(slug)

    payload = {
        "title": title,
        "content": content,
        "excerpt": excerpt,
        "slug": slug,
        "status": "publish",
    }

    if existing:
        page_id = existing["id"]
        resp = requests.post(
            f"{API_BASE}/pages/{page_id}",
            json=payload,
            auth=AUTH,
            timeout=30,
        )
        action = "更新"
    else:
        resp = requests.post(
            f"{API_BASE}/pages",
            json=payload,
            auth=AUTH,
            timeout=30,
        )
        action = "新規作成"

    resp.raise_for_status()
    result = resp.json()
    print(f"  ✓ [{action}] {title} → {result.get('link', '')}")
    return result


# ──────────────────────────────────────────────
# HTML 生成 — 公立高校入試情報
# ──────────────────────────────────────────────
def build_public_exam_html(data: dict) -> str:
    updated = datetime.fromisoformat(data["updated_at"]).strftime("%Y年%m月%d日")
    schedule = data.get("schedule", {})
    schools = data.get("schools", [])

    # 入試日程セクション
    schedule_html = ""
    if schedule.get("schedule"):
        rows = "\n".join(
            f'<tr><td>{s["event"]}</td><td>{s["date"]}</td></tr>'
            for s in schedule["schedule"]
        )
        schedule_html = f"""
<h2>📅 入試日程（2027年度）</h2>
<table>
<thead><tr><th>区分</th><th>日程</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="wp-block-paragraph">
  <a href="{schedule.get('official_url', 'https://www.kyoto-be.ne.jp/ed-top/')}" target="_blank" rel="noopener">
    ▶ 京都府教育委員会 公式サイトで確認する
  </a>
</p>
"""
    elif schedule.get("links"):
        links_html = "\n".join(
            f'<li><a href="{l["url"]}" target="_blank" rel="noopener">{l["text"]}</a></li>'
            for l in schedule["links"][:8]
        )
        schedule_html = f"""
<h2>📅 入試日程・関連情報</h2>
<ul>{links_html}</ul>
"""

    # 学校一覧セクション
    school_rows = ""
    for s in schools[:30]:
        bairitsu_latest = "—"
        if s.get("bairitsu") and s["bairitsu"]:
            b = s["bairitsu"][0]
            bairitsu_latest = b.get("ratio", "—")

        school_rows += (
            f'<tr>'
            f'<td><a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a></td>'
            f'<td>{s.get("hensachi", "—")}</td>'
            f'<td>{bairitsu_latest}</td>'
            f'<td>{s.get("area", "—")}</td>'
            f'</tr>\n'
        )

    school_section = f"""
<h2>🏫 学校別 偏差値・倍率一覧</h2>
<p>出典：<a href="https://www.minkou.jp/" target="_blank" rel="noopener">みんなの高校情報</a></p>
<table>
<thead>
<tr><th>学校名</th><th>偏差値</th><th>最新倍率</th><th>所在地</th></tr>
</thead>
<tbody>
{school_rows if school_rows else '<tr><td colspan="4">情報収集中です</td></tr>'}
</tbody>
</table>
""" if schools else ""

    return f"""
<!-- wp:html -->
<div class="kyoto-exam-info">
<div class="exam-updated-notice" style="background:#f0f7ff;border-left:4px solid #3b82f6;padding:12px 16px;margin-bottom:24px;border-radius:4px;">
  📅 最終更新: {updated}（自動更新）
</div>

{schedule_html}

{school_section}

<div class="exam-disclaimer" style="background:#fff9e6;border:1px solid #fbbf24;padding:16px;margin-top:32px;border-radius:4px;font-size:0.9em;">
  <strong>⚠️ ご注意</strong><br>
  掲載情報は自動収集データです。受験を検討される際は必ず各学校・京都府教育委員会の公式サイトで最新情報をご確認ください。
</div>
</div>
<!-- /wp:html -->
"""


# ──────────────────────────────────────────────
# HTML 生成 — 説明会・OC 情報
# ──────────────────────────────────────────────
def build_events_html(data: dict) -> str:
    updated = datetime.fromisoformat(data["updated_at"]).strftime("%Y年%m月%d日")
    calendar = data.get("events", {}).get("calendar", [])
    official = data.get("events", {}).get("official", [])
    private_schools = data.get("private_schools", [])

    # カレンダーイベント
    calendar_rows = "\n".join(
        f'<tr><td>{e.get("date","—")}</td><td>{e.get("school","—")}</td><td>{e.get("event","—")}</td></tr>'
        for e in calendar[:20]
    ) if calendar else '<tr><td colspan="3">現在登録なし（随時更新）</td></tr>'

    # 公式サイト情報
    official_items = "\n".join(
        f'<li><strong>{e["school"]}</strong>：{e["text"]} '
        f'（<a href="{e["source"]}" target="_blank" rel="noopener">公式サイト</a>）</li>'
        for e in official[:15]
    ) if official else "<li>情報収集中です</li>"

    # 私立高校一覧（上位20校）
    private_rows = "\n".join(
        f'<tr><td><a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a></td>'
        f'<td>{s.get("hensachi","—")}</td><td>{s.get("area","—")}</td></tr>'
        for s in private_schools[:20]
    ) if private_schools else '<tr><td colspan="3">情報収集中です</td></tr>'

    return f"""
<!-- wp:html -->
<div class="kyoto-exam-info">
<div class="exam-updated-notice" style="background:#f0f7ff;border-left:4px solid #3b82f6;padding:12px 16px;margin-bottom:24px;border-radius:4px;">
  📅 最終更新: {updated}（毎週月曜自動更新）
</div>

<h2>🗓️ 説明会・オープンキャンパス 直近日程</h2>
<table>
<thead><tr><th>日程</th><th>学校名</th><th>イベント</th></tr></thead>
<tbody>{calendar_rows}</tbody>
</table>

<h2>📢 各校公式サイト情報</h2>
<ul>{official_items}</ul>

<h2>🏫 京都府私立高校 偏差値一覧</h2>
<p>出典：<a href="https://www.minkou.jp/" target="_blank" rel="noopener">みんなの高校情報</a></p>
<table>
<thead><tr><th>学校名</th><th>偏差値</th><th>所在地</th></tr></thead>
<tbody>{private_rows}</tbody>
</table>

<div class="exam-disclaimer" style="background:#fff9e6;border:1px solid #fbbf24;padding:16px;margin-top:32px;border-radius:4px;font-size:0.9em;">
  <strong>⚠️ ご注意</strong><br>
  掲載情報は自動収集データです。イベントの詳細・変更は必ず各学校の公式サイトでご確認ください。
</div>
</div>
<!-- /wp:html -->
"""


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────
def main():
    if not all([WP_URL, WP_USER, WP_APP_PASSWORD]):
        print("エラー: 環境変数 WP_URL / WP_USER / WP_APP_PASSWORD が未設定です")
        sys.exit(1)

    print(f"[wp_update] WordPress 更新開始 → {WP_URL}")

    # 公立高校入試情報ページ
    public_path = DATA_DIR / "public_exam.json"
    if public_path.exists():
        with open(public_path, encoding="utf-8") as f:
            public_data = json.load(f)

        content = build_public_exam_html(public_data)
        create_or_update_page(
            slug="kyoto-kouritsu-exam",
            title="京都府 公立高校 入試情報まとめ【2027年度】",
            content=content,
            excerpt="京都府の公立高校入試日程・偏差値・倍率を自動収集してまとめています。",
        )
    else:
        print("  ⚠ public_exam.json が見つかりません")

    # 私立高校・説明会情報ページ
    events_path = DATA_DIR / "school_events.json"
    if events_path.exists():
        with open(events_path, encoding="utf-8") as f:
            events_data = json.load(f)

        # 私立受験情報ページ
        private_content = build_events_html(events_data)
        create_or_update_page(
            slug="kyoto-shiritsu-exam",
            title="京都府 私立高校 受験情報・説明会日程まとめ",
            content=private_content,
            excerpt="京都府の私立高校偏差値・説明会・オープンキャンパス日程を自動収集してまとめています。",
        )
    else:
        print("  ⚠ school_events.json が見つかりません")

    print("[wp_update] 完了")


if __name__ == "__main__":
    main()
