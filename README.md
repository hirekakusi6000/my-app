# オフィス座席・従業員管理システム

オフィスの座席配置、出勤・在席状況、プロフィール、技術スキルを一元管理する Web アプリケーション。

設計書は [docs/](docs/) にあります（要件・アーキテクチャ・ディレクトリ・DB・API・画面）。
公開する手順は [docs/07-deployment.md](docs/07-deployment.md) を参照してください。

## 技術構成

- バックエンド: Python 3.12+ / FastAPI
- フロントエンド: HTML / CSS / JavaScript（フレームワーク不使用）
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

- アプリ: http://127.0.0.1:8000
- API 仕様書: http://127.0.0.1:8000/docs
- 停止: ターミナルで Ctrl + C

## よく使うコマンド

```powershell
pytest                                 # テスト
pytest --cov=app                       # カバレッジ付きテスト
ruff check . ; ruff format .           # lint と整形
python -m app.db.migrate               # マイグレーションを手動で実行
python -m app.db.backup                # DB とプロフィール画像のバックアップ
```

## ブランチ運用

- `master`: リリース用
- `develop`: 開発の統合用
- `feature/<名前>`: 機能ごとの作業ブランチ（`develop` から作成し、`develop` にマージ）
