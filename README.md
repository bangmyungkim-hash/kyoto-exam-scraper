# 京都高校受験情報 自動収集システム

京都府の高校受験情報を自動スクレイピングし、aioijuku.com (WordPress) に自動更新するシステム。

## 構成

```
.github/workflows/
  weekly-scrape.yml   毎週月曜 AM6:00 JST に自動実行

scrapers/
  public_exam.py      公立高校 入試日程・偏差値・倍率
  school_events.py    私立高校 + 説明会・オープンキャンパス

publisher/
  wp_update.py        WordPress REST API でページ更新

data/                 収集データ（JSON）を自動コミット
```

## 更新されるWordPressページ

| スラッグ | タイトル | 更新頻度 |
|---|---|---|
| `kyoto-kouritsu-exam` | 京都府 公立高校 入試情報まとめ | 週1回 |
| `kyoto-shiritsu-exam` | 京都府 私立高校 受験情報・説明会日程まとめ | 週1回 |

## セットアップ手順

### 1. WordPress アプリケーションパスワードを発行

WordPress 管理画面 → ユーザー → プロフィール → アプリケーションパスワード
→「kyoto-exam-scraper」という名前で新規発行
→ 表示されたパスワードをコピー（再表示不可）

### 2. GitHub Secrets に登録

GitHub リポジトリ → Settings → Secrets and variables → Actions → New repository secret

| Secret名 | 値 |
|---|---|
| `WP_URL` | `https://aioijuku.com` |
| `WP_USER` | WordPress ユーザー名 |
| `WP_APP_PASSWORD` | 手順1で発行したパスワード |

### 3. 手動テスト実行

GitHub → Actions タブ → 「京都高校受験情報 週次収集・WordPress更新」
→「Run workflow」ボタンで手動実行できます

## ローカル実行（テスト用）

```bash
pip install -r requirements.txt

# スクレイピング
python scrapers/public_exam.py
python scrapers/school_events.py

# WordPress 更新（環境変数を設定してから）
export WP_URL=https://aioijuku.com
export WP_USER=your_username
export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"
python publisher/wp_update.py
```

## データソース

- 京都府教育委員会: https://www.kyoto-be.ne.jp/ed-top/
- みんなの高校情報: https://www.minkou.jp/hischool/search/pref_id=26/
- 各私立高校公式サイト

掲載情報の最終判断は必ず公式サイトでご確認ください。
