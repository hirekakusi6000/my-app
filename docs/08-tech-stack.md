# 08. 使用技術

このアプリで使っている技術の一覧。バージョンは `requirements.txt` / `requirements-dev.txt` で固定しているもの。

## バックエンド
| 技術 | バージョン | 用途 |
|---|---|---|
| Python | 3.14（3.12 以上で動作） | 開発言語 |
| FastAPI | 0.162.0 | Web フレームワーク（REST API、入力チェック、API 仕様書の自動生成） |
| Uvicorn | 0.54.0 | ASGI サーバー（アプリの起動・公開） |
| Pydantic | 2.x（FastAPI に同梱） | API の入出力の型と入力チェック |
| pydantic-settings | 2.16.2 | 設定の読み込み（環境変数・`.env`） |
| SQLite（`sqlite3`） | Python 標準 | データベース。ORM は使わず生 SQL で操作 |
| argon2-cffi | 25.1.0 | パスワードのハッシュ化（Argon2） |
| email-validator | 2.3.0 | メールアドレスの形式チェック |
| python-multipart | 0.0.33 | ファイルのアップロード（プロフィール画像・CSV） |

## フロントエンド
| 技術 | 用途 |
|---|---|
| HTML / CSS / JavaScript（フレームワーク不使用） | すべての画面 |
| ES モジュール（`import` / `export`） | 画面ごと・部品ごとにスクリプトを分割（`frontend/js/`） |
| SVG | オフィスマップの描画と編集（ドラッグ、範囲選択、回転） |
| Fetch API | API の呼び出し（共通処理は `frontend/js/api/client.js` に集約） |
| `<dialog>` 要素 | 確認・入力のダイアログ |
| CSS カスタムプロパティ | 色などのデザインの共通化 |

## 設計・アーキテクチャ
詳しくは [02-architecture.md](02-architecture.md) を参照。

| 項目 | 内容 |
|---|---|
| レイヤー構成 | API（router）→ service（業務ルール）→ repository（SQL）の一方向。DB アクセスと業務ロジックを分離 |
| マルチテナント | すべてのデータを `organization_id` で組織ごとに分離。他の組織のデータは 404 |
| マイグレーション | 番号付きの SQL ファイル（`migrations/`）＋ `PRAGMA user_version` による自作の仕組み |
| 認証 | セッション Cookie（`HttpOnly`・`SameSite=Lax`）。トークンは DB にハッシュ値で保存 |
| 認可 | FastAPI の `Depends` による権限チェック（マスター／一般、初回設定の完了） |
| データの保護 | UNIQUE・CHECK・外部キーの制約（座席の重複防止など）、プレースホルダーによる SQL インジェクション対策 |

## セキュリティ・運用
詳しくは [07-deployment.md](07-deployment.md) を参照。

| 項目 | 内容 |
|---|---|
| セキュリティヘッダー | CSP、X-Frame-Options、HSTS（HTTPS 時）、Referrer-Policy、Permissions-Policy |
| 試行回数の制限 | ログインと新規登録（メモリ上のスライディングウィンドウ） |
| ログ | Python 標準の `logging`。リクエストID、アクセスログ、監査ログ、ファイルのローテーション |
| バックアップ | SQLite のバックアップ機能（動作中でも安全）＋世代管理（`python -m app.db.backup`） |
| 公開 | Caddy / nginx（HTTPS とリバースプロキシ）、systemd の設定例 |

## テスト・品質
| 技術 | バージョン | 用途 |
|---|---|---|
| pytest | 9.2.0 | テスト全般（単体・API・画面） |
| pytest-cov | 7.1.0 | カバレッジの計測（CI では 90% 未満で失敗） |
| httpx（FastAPI の `TestClient`） | 0.28.1 | API のテスト |
| Playwright（pytest-playwright） | 1.65.0 / 0.10.0 | 画面の自動テスト（Chromium で主な操作の流れを確認） |
| Node.js（`node --check`） | 18 以上 | 画面の JavaScript の文法チェック |
| Ruff | 0.17.4 | lint と整形 |
| `.editorconfig` / `.gitattributes` | ― | 文字コード（UTF-8）・改行コード（LF）の統一 |

## 開発環境・CI
| 技術 | 用途 |
|---|---|
| pip / venv | ライブラリの管理と仮想環境 |
| Git | バージョン管理。`master` ← `develop` ← `feature/*`、`--no-ff` でマージ |
| GitHub Actions | lint・テスト（Python 3.12 / 3.14）・画面の自動テストの自動実行（`.github/workflows/ci.yml`） |
| Dependabot | ライブラリと GitHub Actions の更新のお知らせ（`.github/dependabot.yml`） |
