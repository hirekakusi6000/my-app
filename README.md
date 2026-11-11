# オフィス座席・従業員管理システム

オフィスの座席配置、出勤・在席状況、プロフィール、技術スキルを一元管理する Web アプリケーションの **API**（FastAPI）です。
画面（Vue 3 + Vite + TypeScript）は別のリポジトリ（`my-app-web`）にあります。

設計書は [docs/](docs/) にあります（要件・アーキテクチャ・ディレクトリ・DB・API・画面）。
公開する手順は [docs/07-deployment.md](docs/07-deployment.md) を参照してください。

## 技術構成

- バックエンド: Python 3.12+ / FastAPI
- フロントエンド: 別のリポジトリ（`my-app-web`。Vue 3 + Vite + TypeScript）
  - 画面と API は同じオリジンで動かす。開発時は Vite の開発サーバーが `/api` をこの API に転送し、公開時はリバースプロキシで振り分ける
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

# 3. 設定ファイル（任意。なければ既定値で動きます）
Copy-Item .env.example .env

# 4. 起動（DB は起動時に自動で作成・マイグレーションされます）
uvicorn app.main:app --reload --reload-dir app
```

- API: http://127.0.0.1:8000/api/v1/...
- API 仕様書: http://127.0.0.1:8000/docs
- 停止: ターミナルで Ctrl + C
- 画面は、画面のリポジトリで `npm run dev` を実行して http://127.0.0.1:5173 を開く（そちらの README を参照）

## よく使うコマンド

```powershell
pytest                                 # テスト
pytest --cov=app                       # カバレッジ付きテスト
ruff check . ; ruff format .           # lint と整形
python -m app.db.migrate               # マイグレーションを手動で実行
python -m app.db.backup                # DB とプロフィール画像のバックアップ
```

## CI（GitHub Actions）

GitHub に push すると、[.github/workflows/ci.yml](.github/workflows/ci.yml) が次を自動で実行します（`master` / `develop` / `feature/**` への push と、プルリクエスト）。

- lint と整形のチェック（ruff）
- テスト（Python 3.12 と 3.14）。カバレッジが 90% 未満なら失敗

画面の自動テスト（Playwright）は、画面のリポジトリの CI がこの API を起動して実行します。

ライブラリと GitHub Actions の更新は、Dependabot が `develop` 向けのプルリクエストで知らせます（[.github/dependabot.yml](.github/dependabot.yml)）。

## ブランチ運用

- `master`: リリース用
- `develop`: 開発の統合用
- `feature/<名前>`: 機能ごとの作業ブランチ（`develop` から作成し、`develop` にマージ）
