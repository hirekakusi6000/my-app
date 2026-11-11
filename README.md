# オフィス座席・従業員管理システム

オフィスの座席配置、出勤・在席状況、プロフィール、技術スキルを一元管理する Web アプリケーション。

設計書は [docs/](docs/) にあります（要件・アーキテクチャ・ディレクトリ・DB・API・画面）。
公開する手順は [docs/07-deployment.md](docs/07-deployment.md) を参照してください。

## 技術構成

- バックエンド: Python 3.12+ / FastAPI
- フロントエンド: Vue 3 + Vite + TypeScript（`web/`）。移行前の画面は HTML / CSS / JavaScript（`frontend/`）
  - 画面ごとに Vue へ順番に移行中。同じ URL のファイルは `web/dist`（Vue のビルド結果）を優先して配信する
- データベース: SQLite（標準ライブラリ `sqlite3`、生SQL）
- ASGIサーバー: Uvicorn
- パッケージ管理: pip

## ローカル開発環境の構築（Windows / PowerShell）

```powershell
# 1. 仮想環境の作成と有効化
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 依存ライブラリのインストール
pip install -r requirements-dev.txt
python -m playwright install chromium  # 画面の自動テスト用のブラウザ（初回のみ）

# 3. Vue の画面のビルド（Node.js 22.12 以上が必要）
cd web; npm install; npm run build; cd ..

# 4. 設定ファイル（任意。なければ既定値で動きます）
Copy-Item .env.example .env

# 5. 起動（DB は起動時に自動で作成・マイグレーションされます）
uvicorn app.main:app --reload --reload-dir app
```

- アプリ: http://127.0.0.1:8000
- API 仕様書: http://127.0.0.1:8000/docs
- 停止: ターミナルで Ctrl + C
- Vue の画面を編集するときは、別のターミナルで `cd web; npm run dev` を実行しておく（保存するたびに `web/dist` を作り直す。ブラウザは再読み込みで反映）

### Vue の画面を追加・移行するとき
1. `web/<URL のパス>.html`（例：`web/admin/organization.html`）と `web/src/pages/` に入口（`.ts`）と画面（`.vue`）を作る
2. `web/vite.config.ts` の `PAGES` に追加する
3. 移行前の `frontend/` の HTML と `frontend/js/pages/` の JS を削除する
- 移行していない共通の処理（API の呼び出し・ヘッダー・ログイン確認など）は `@legacy/...`（= `frontend/`）から読み込める
- CSP でインラインのスクリプト・スタイルを禁止しているので、`<style>` の代わりに CSS ファイル（または `.vue` の `<style>`。ビルドでファイルに書き出される）を使う

## よく使うコマンド

```powershell
pytest                                 # テスト（画面の自動テストを含む）
pytest -m "not e2e"                    # 画面の自動テストを除く（速い）
pytest -m e2e --headed                 # 画面の自動テストを、ブラウザを表示しながら実行
pytest --cov=app                       # カバレッジ付きテスト
ruff check . ; ruff format .           # lint と整形
cd web; npm run typecheck              # Vue の画面の型チェック
python -m app.db.migrate               # マイグレーションを手動で実行
python -m app.db.backup                # DB とプロフィール画像のバックアップ
```

## CI（GitHub Actions）

GitHub に push すると、[.github/workflows/ci.yml](.github/workflows/ci.yml) が次を自動で実行します（`master` / `develop` / `feature/**` への push と、プルリクエスト）。

- lint と整形のチェック（ruff）
- Vue の画面の型チェックとビルド（vue-tsc / Vite）
- テスト（Python 3.12 と 3.14）。カバレッジが 90% 未満なら失敗
- 画面の JavaScript の文法チェック（`tests/unit/test_frontend_syntax.py`。ローカルでも Node.js があれば実行される）
- 画面の自動テスト（`tests/e2e`。Playwright の Chromium で主な操作の流れを確認。失敗時はスクリーンショットと操作の記録を保存）

ライブラリと GitHub Actions の更新は、Dependabot が `develop` 向けのプルリクエストで知らせます（[.github/dependabot.yml](.github/dependabot.yml)）。

## ブランチ運用

- `master`: リリース用
- `develop`: 開発の統合用
- `feature/<名前>`: 機能ごとの作業ブランチ（`develop` から作成し、`develop` にマージ）
