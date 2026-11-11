# 07. 公開（デプロイ）手順

インターネットに公開して他の人に試してもらうための設定と手順。

## 1. 前提
| 項目 | 内容 |
|---|---|
| プロセス数 | **1つ**（`--workers 1`）。SQLite への書き込みと、ログイン回数制限（メモリ上で数える）を1プロセスで扱う設計のため |
| ディスク | `data/`（DB・プロフィール画像・バックアップ・ログ）を**再起動しても消えないディスク**に置く。サーバーレス（ディスクが毎回消える環境）は使えない |
| HTTPS | 必須。ログインの Cookie とパスワードを守るため |
| 公開先の例 | VPS（さくらの VPS、ConoHa、Lightsail など）、または永続ボリュームを付けられる PaaS（Fly.io の Volume、Render の Disk など） |

## 2. 環境変数（`.env`）
`.env.example` をコピーして作る。公開時に**変える必要があるもの**は太字。

| 変数 | 開発時の値 | 公開時の推奨 | 内容 |
|---|---|---|---|
| **`APP_COOKIE_SECURE`** | `false` | **`true`** | Cookie に `Secure` を付け、HSTS ヘッダーを送る |
| **`APP_ENABLE_API_DOCS`** | `true` | **`false`** | `/docs`（API 仕様書）を公開するか |
| `APP_LOG_FILE` | なし | `data/logs/app.log` | ログをファイルにも出す（10MB ごとに切り替え、5世代） |
| `APP_LOG_LEVEL` | `INFO` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `APP_DATABASE_PATH` | `data/app.db` | 永続ディスク上のパス | SQLite のファイル |
| `APP_UPLOAD_DIR` | `data/uploads` | 永続ディスク上のパス | プロフィール画像 |
| `APP_BACKUP_DIR` | `data/backups` | 永続ディスク上のパス | バックアップの保存先 |
| `APP_BACKUP_KEEP` | `14` | `14` | 残すバックアップの数 |
| `APP_SESSION_EXPIRE_HOURS` | `168` | `168` | ログインの有効期限（時間） |

起動時に `APP_COOKIE_SECURE が false です` という警告がログに出たら、設定を見直す。

## 3. 起動
アプリは `127.0.0.1` だけで待ち受け、前段のリバースプロキシ（HTTPS を担当）から転送してもらう。

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 \
  --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log
```

- `--proxy-headers --forwarded-allow-ips 127.0.0.1`：プロキシが付けた `X-Forwarded-For` から**利用者の本当の IP** を取り出す。これがないと、すべての利用者が「プロキシの IP」に見え、ログイン回数制限が全員まとめて効いてしまう。信頼するプロキシの IP だけを指定すること
- `--no-access-log`：アクセスログはアプリが（リクエストID 付きで）出すので、Uvicorn の分は止める
- DB のマイグレーションは起動時に自動で適用される
- サーバーの起動・自動再起動は systemd などに任せる（例は下記）

```ini
# /etc/systemd/system/office-seat.service
[Unit]
Description=Office seat manager
After=network.target

[Service]
WorkingDirectory=/srv/my-app
EnvironmentFile=/srv/my-app/.env
ExecStart=/srv/my-app/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log
Restart=always
User=office-seat

[Install]
WantedBy=multi-user.target
```

## 4. リバースプロキシと HTTPS
### Caddy（おすすめ：証明書を自動で取得・更新する）
```
seat.example.com {
    reverse_proxy 127.0.0.1:8000
    request_body {
        max_size 3MB
    }
}
```

### nginx の場合
```nginx
server {
    listen 443 ssl;
    server_name seat.example.com;
    # ssl_certificate / ssl_certificate_key は Let's Encrypt（certbot）などで用意する
    client_max_body_size 3m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
`max_size` / `client_max_body_size` は、プロフィール画像（2MB）と CSV（100KB）より少し大きくしておく。

## 5. セキュリティヘッダー
アプリがすべての応答に付ける（`app/core/middleware.py`）。

| ヘッダー | 値 | 目的 |
|---|---|---|
| `Content-Security-Policy` | 自分のサーバーのファイルだけを許可。インラインのスクリプト・スタイルは禁止 | XSS の被害を抑える |
| `X-Frame-Options` / `frame-ancestors` | `DENY` / `'none'` | 他のサイトに埋め込ませない（クリックジャッキング対策） |
| `X-Content-Type-Options` | `nosniff` | ファイルの種類の誤認を防ぐ |
| `Referrer-Policy` | `same-origin` | 他のサイトに URL を渡さない |
| `Permissions-Policy` | カメラ・マイク・位置情報を無効 | 使わない機能を止める |
| `Strict-Transport-Security` | `APP_COOKIE_SECURE=true` のときだけ | 以後 HTTPS でしか接続させない |

`/docs`（Swagger UI）は外部の CDN を読むため CSP を付けない。公開時は `APP_ENABLE_API_DOCS=false` で無効にする。

## 6. ログ
```
2026-11-07 13:44:01 INFO  app.access [3f9c2a1b7e0d4c55] 203.0.113.5 POST /api/v1/auth/login 401 52ms
2026-11-07 13:44:01 WARNING app.audit [3f9c2a1b7e0d4c55] ログインに失敗しました email=ta***@example.com
```
| ロガー | 内容 |
|---|---|
| `app.access` | API と画面のアクセス（IP・メソッド・パス・ステータス・処理時間）。CSS・JS などは省略 |
| `app.audit` | 組織の作成・削除、ログインの成功・失敗、回数制限、ユーザーの削除 |
| `app.error` | 予期しないエラー（スタックトレース付き） |

- `[...]` はリクエストID。応答ヘッダー `X-Request-ID` と同じ値で、予期しないエラーのときは画面にも返す。利用者から問い合わせがあれば、この ID でログを探す
- パスワード・セッションのトークンはログに出さない。メールアドレスは一部を伏せる

## 7. バックアップと復元
### バックアップ（毎日1回）
```bash
# アプリを止めずに実行できる。data/backups/20261107-031500/ に app.db と uploads/ を保存し、古いものを削除する
python -m app.db.backup
```
cron の例（毎日 3:15）:
```
15 3 * * * cd /srv/my-app && .venv/bin/python -m app.db.backup >> data/logs/backup.log 2>&1
```
Windows ではタスクスケジューラに `.venv\Scripts\python.exe -m app.db.backup` を登録する。
**同じサーバーのディスクが壊れると一緒に消える**ので、`data/backups` は定期的に別の場所（オブジェクトストレージなど）にも複製する。

### 復元
1. アプリを止める
2. `data/app.db`（と、あれば `app.db-wal` `app.db-shm`）を退避する
3. バックアップの `app.db` を `data/app.db` に、`uploads/` を `data/uploads/` にコピーする
4. アプリを起動する

## 8. 公開前のチェックリスト
- [ ] `APP_COOKIE_SECURE=true`、`APP_ENABLE_API_DOCS=false`
- [ ] HTTPS で開け、`http://` は `https://` に転送される
- [ ] `--proxy-headers --forwarded-allow-ips` を設定し、ログの IP が利用者の IP になっている
- [ ] `--workers 1` で起動している
- [ ] `data/` が永続ディスク上にあり、再起動しても消えない
- [ ] バックアップが毎日作られ、別の場所にも複製されている。復元を一度試した
- [ ] ログがファイルに出ており、ディスクを圧迫していない
