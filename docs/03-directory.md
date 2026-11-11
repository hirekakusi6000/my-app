# 03. ディレクトリ構成

```
my-app/
├─ app/
│  ├─ main.py                    # アプリの組み立て（ルーター、例外ハンドラー、画面ファイルの配信、起動時のマイグレーション）
│  ├─ core/
│  │  ├─ config.py               # 設定（.env）
│  │  ├─ security.py             # パスワードのハッシュ化、セッショントークン
│  │  ├─ errors.py               # 業務エラーと HTTP エラーへの変換
│  │  └─ rate_limit.py           # ログイン・新規登録の回数制限
│  ├─ db/
│  │  ├─ connection.py           # 接続、PRAGMA 設定、get_db
│  │  └─ migrate.py              # migrations/*.sql を番号順に実行
│  ├─ entities/                  # 内部で使うデータ型（dataclass）
│  ├─ schemas/                   # API の入出力（Pydantic）
│  ├─ repositories/              # 生SQL（organization_id で必ず絞り込む）
│  ├─ services/                  # 業務ルール
│  └─ api/
│     ├─ deps.py                 # 共通の Depends
│     └─ v1/
│        ├─ router.py
│        └─ endpoints/           # auth / me / users / profiles / skills / master_data /
│                                # floors / rooms / presence / health
├─ migrations/                   # 0001_init.sql, 0002_xxx.sql ...
├─ web/                          # Vue 3 + Vite + TypeScript の画面
│  ├─ admin/*.html               # 画面の入口（URL と同じパス。Vite のビルドの入力）
│  ├─ src/
│  │  ├─ pages/                  # 画面ごとの入口（.ts）と画面（.vue）
│  │  ├─ api/                    # API の呼び出し（型付き）
│  │  ├─ lib/                    # 共通の処理
│  │  └─ types/                  # API の応答の型
│  ├─ vite.config.ts             # 画面の一覧（PAGES）、@legacy → frontend/
│  ├─ package.json / package-lock.json
│  └─ dist/                      # ビルド結果（git 管理外。FastAPI が frontend/ より優先して配信）
├─ frontend/                     # Vue に移行する前の画面（順番に web/ へ移行する）
│  ├─ *.html                     # 共通・一般ユーザー向けの画面
│  ├─ admin/*.html               # マスター向けの画面
│  ├─ css/                       # base.css, components.css, map.css
│  └─ js/
│     ├─ api/                    # client.js（fetch の共通処理）とリソースごとの API 呼び出し
│     ├─ components/             # map-renderer.js、profile-modal.js など
│     ├─ lib/                    # auth-guard.js、dom.js
│     └─ pages/                  # 画面ごとの処理
├─ tests/
│  ├─ conftest.py
│  ├─ unit/                      # service・DB のテスト
│  └─ api/                       # API のテスト
├─ docs/                         # 設計書
├─ data/                         # app.db、uploads/（git 管理外）
├─ requirements.txt / requirements-dev.txt
├─ pyproject.toml                # pytest・ruff の設定
└─ .env.example
```

## 命名規則
- Python：ファイル・関数は `snake_case`、クラスは `PascalCase`。ファイル名は `<リソース>_repository.py` / `<リソース>_service.py`
- API のパス：複数形の名詞、単語の区切りは `-`（例：`/job-types`）
- JSON のキー：`snake_case`
- JS / TS：ファイルは `kebab-case.js` / `kebab-case.ts`、関数・変数は `camelCase`
- Vue：コンポーネントのファイルは `PascalCase.vue`
