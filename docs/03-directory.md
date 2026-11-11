# 03. ディレクトリ構成

```
my-app/
├─ app/
│  ├─ main.py                    # アプリの組み立て（ルーター、例外ハンドラー、起動時のマイグレーション）
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

画面（Vue 3 + Vite + TypeScript）は別のリポジトリ（`my-app-web`）。ディレクトリはそちらの README を参照。

## 命名規則
- Python：ファイル・関数は `snake_case`、クラスは `PascalCase`。ファイル名は `<リソース>_repository.py` / `<リソース>_service.py`
- API のパス：複数形の名詞、単語の区切りは `-`（例：`/job-types`）
- JSON のキー：`snake_case`
- JS / TS：ファイルは `kebab-case.js` / `kebab-case.ts`、関数・変数は `camelCase`
- Vue：コンポーネントのファイルは `PascalCase.vue`
