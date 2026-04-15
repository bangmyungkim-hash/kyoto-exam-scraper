"""
wp_update.py
収集データから HTML + PHP 更新スクリプトを生成する

GitHub Actions がこのスクリプトを実行後、
生成されたファイルを SCP で Xserver に転送し
WP-CLI で WordPress ページを更新する。
"""

import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PAGES = [
    {
        "slug": "kyoto-kouritsu-exam",
        "title": "京都府 公立高校 入試情報まとめ【2027年度】",
        "excerpt": "京都府の公立高校入試日程・偏差値・倍率を自動収集してまとめています。",
        "data_file": "public_exam.json",
    },
    {
        "slug": "kyoto-shiritsu-exam",
        "title": "京都府 私立高校 受験情報・説明会日程まとめ",
        "excerpt": "京都府の私立高校偏差値・説明会・オープンキャンパス日程を自動収集してまとめています。",
        "data_file": "school_events.json",
    },
]


# ──────────────────────────────────────────────
# HTML 生成 — 公立高校入試情報
# ──────────────────────────────────────────────
def build_public_exam_html(data: dict) -> str:
    updated = datetime.fromisoformat(data["updated_at"]).strftime("%Y年%m月%d日")
    schedule = data.get("schedule", {})
    schools = data.get("schools", [])

    schedule_html = ""
    if schedule.get("schedule"):
        rows = "\n".join(
            f'<tr><td>{s["event"]}</td><td>{s["date"]}</td></tr>'
            for s in schedule["schedule"]
        )
        schedule_html = f"""
<h2>入試日程（2027年度）</h2>
<table>
<thead><tr><th>区分</th><th>日程</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p><a href="{schedule.get('official_url', 'https://www.kyoto-be.ne.jp/ed-top/')}" target="_blank" rel="noopener">
▶ 京都府教育委員会 公式サイトで確認する
</a></p>
"""
    elif schedule.get("links"):
        links_html = "\n".join(
            f'<li><a href="{l["url"]}" target="_blank" rel="noopener">{l["text"]}</a></li>'
            for l in schedule["links"][:8]
        )
        schedule_html = f"<h2>入試日程・関連情報</h2><ul>{links_html}</ul>"

    school_rows = ""
    for s in schools[:30]:
        bairitsu_latest = "—"
        if s.get("bairitsu"):
            bairitsu_latest = s["bairitsu"][0].get("ratio", "—")
        school_rows += (
            f'<tr><td><a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a></td>'
            f'<td>{s.get("hensachi", "—")}</td>'
            f'<td>{bairitsu_latest}</td>'
            f'<td>{s.get("area", "—")}</td></tr>\n'
        )

    school_section = f"""
<h2>学校別 偏差値・倍率一覧</h2>
<p>出典：<a href="https://www.minkou.jp/" target="_blank" rel="noopener">みんなの高校情報</a></p>
<table>
<thead><tr><th>学校名</th><th>偏差値</th><th>最新倍率</th><th>所在地</th></tr></thead>
<tbody>{school_rows or '<tr><td colspan="4">情報収集中です</td></tr>'}</tbody>
</table>
""" if schools else ""

    return f"""<!-- wp:html -->
<div class="kyoto-exam-info">
<div style="background:#f0f7ff;border-left:4px solid #3b82f6;padding:12px 16px;margin-bottom:24px;border-radius:4px;">
最終更新: {updated}（自動更新）
</div>
{schedule_html}
{school_section}
<div style="background:#fff9e6;border:1px solid #fbbf24;padding:16px;margin-top:32px;border-radius:4px;font-size:0.9em;">
<strong>ご注意</strong><br>
掲載情報は自動収集データです。受験前に必ず各学校・京都府教育委員会の公式サイトでご確認ください。
</div>
</div>
<!-- /wp:html -->"""


# ──────────────────────────────────────────────
# HTML 生成 — 私立高校・説明会情報
# ──────────────────────────────────────────────
def build_events_html(data: dict) -> str:
    updated = datetime.fromisoformat(data["updated_at"]).strftime("%Y年%m月%d日")
    calendar = data.get("events", {}).get("calendar", [])
    official = data.get("events", {}).get("official", [])
    private_schools = data.get("private_schools", [])

    calendar_rows = "\n".join(
        f'<tr><td>{e.get("date","—")}</td><td>{e.get("school","—")}</td><td>{e.get("event","—")}</td></tr>'
        for e in calendar[:20]
    ) or '<tr><td colspan="3">現在登録なし（随時更新）</td></tr>'

    official_items = "\n".join(
        f'<li><strong>{e["school"]}</strong>：{e["text"]} '
        f'（<a href="{e["source"]}" target="_blank" rel="noopener">公式サイト</a>）</li>'
        for e in official[:15]
    ) or "<li>情報収集中です</li>"

    private_rows = "\n".join(
        f'<tr><td><a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]}</a></td>'
        f'<td>{s.get("hensachi","—")}</td><td>{s.get("area","—")}</td></tr>'
        for s in private_schools[:20]
    ) or '<tr><td colspan="3">情報収集中です</td></tr>'

    return f"""<!-- wp:html -->
<div class="kyoto-exam-info">
<div style="background:#f0f7ff;border-left:4px solid #3b82f6;padding:12px 16px;margin-bottom:24px;border-radius:4px;">
最終更新: {updated}（毎週月曜自動更新）
</div>
<h2>説明会・オープンキャンパス 直近日程</h2>
<table>
<thead><tr><th>日程</th><th>学校名</th><th>イベント</th></tr></thead>
<tbody>{calendar_rows}</tbody>
</table>
<h2>各校公式サイト情報</h2>
<ul>{official_items}</ul>
<h2>京都府私立高校 偏差値一覧</h2>
<p>出典：<a href="https://www.minkou.jp/" target="_blank" rel="noopener">みんなの高校情報</a></p>
<table>
<thead><tr><th>学校名</th><th>偏差値</th><th>所在地</th></tr></thead>
<tbody>{private_rows}</tbody>
</table>
<div style="background:#fff9e6;border:1px solid #fbbf24;padding:16px;margin-top:32px;border-radius:4px;font-size:0.9em;">
<strong>ご注意</strong><br>
掲載情報は自動収集データです。イベントの詳細・変更は必ず各学校の公式サイトでご確認ください。
</div>
</div>
<!-- /wp:html -->"""


# ──────────────────────────────────────────────
# PHP 更新スクリプト生成（WP-CLI eval-file 用）
# ──────────────────────────────────────────────
def generate_php_script() -> str:
    pages_json = json.dumps(PAGES, ensure_ascii=False)
    return f"""<?php
$pages = json_decode('{pages_json}', true);
$tmp_dir = '/tmp/kyoto-exam';

foreach ($pages as $page) {{
    $slug    = $page['slug'];
    $title   = $page['title'];
    $excerpt = $page['excerpt'];
    $html    = file_get_contents($tmp_dir . '/' . $slug . '.html');

    if ($html === false) {{
        echo "ERROR: ファイルが見つかりません: $slug\\n";
        continue;
    }}

    $existing = get_page_by_path($slug, OBJECT, 'page');
    if ($existing) {{
        wp_update_post([
            'ID'           => $existing->ID,
            'post_title'   => $title,
            'post_content' => $html,
            'post_excerpt' => $excerpt,
            'post_status'  => 'publish',
        ]);
        echo "Updated: {{$existing->ID}} - $title\\n";
    }} else {{
        $id = wp_insert_post([
            'post_type'    => 'page',
            'post_title'   => $title,
            'post_name'    => $slug,
            'post_content' => $html,
            'post_excerpt' => $excerpt,
            'post_status'  => 'publish',
        ]);
        echo "Created: $id - $title\\n";
    }}
}}
echo "完了\\n";
"""


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────
def main():
    print("[wp_update] HTML・PHPスクリプト生成開始...")

    # 公立高校ページ
    public_path = DATA_DIR / "public_exam.json"
    if public_path.exists():
        with open(public_path, encoding="utf-8") as f:
            public_data = json.load(f)
        html = build_public_exam_html(public_data)
        out = DATA_DIR / "kyoto-kouritsu-exam.html"
        out.write_text(html, encoding="utf-8")
        print(f"  ✓ {out.name}")
    else:
        print("  ⚠ public_exam.json が見つかりません（空のHTMLを生成）")
        fallback = "<p>情報収集中です。しばらくお待ちください。</p>"
        (DATA_DIR / "kyoto-kouritsu-exam.html").write_text(fallback, encoding="utf-8")

    # 私立高校・説明会ページ
    events_path = DATA_DIR / "school_events.json"
    if events_path.exists():
        with open(events_path, encoding="utf-8") as f:
            events_data = json.load(f)
        html = build_events_html(events_data)
        out = DATA_DIR / "kyoto-shiritsu-exam.html"
        out.write_text(html, encoding="utf-8")
        print(f"  ✓ {out.name}")
    else:
        print("  ⚠ school_events.json が見つかりません（空のHTMLを生成）")
        fallback = "<p>情報収集中です。しばらくお待ちください。</p>"
        (DATA_DIR / "kyoto-shiritsu-exam.html").write_text(fallback, encoding="utf-8")

    # PHP スクリプト生成
    php_script = generate_php_script()
    php_path = DATA_DIR / "wp_update.php"
    php_path.write_text(php_script, encoding="utf-8")
    print(f"  ✓ {php_path.name}")

    print("[wp_update] 生成完了")


if __name__ == "__main__":
    main()
