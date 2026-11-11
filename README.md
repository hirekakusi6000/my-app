# オフィス座席・従業員管理システム（API）

オフィスの座席配置・在席状況・プロフィール・スキルを管理する Web アプリの **API**（Python / FastAPI / SQLite）です。

**README と設計書は、ドキュメントのリポジトリ `my-app-docs` にまとめています。**
開発環境の構築・コマンドは `my-app-docs` の `README.md`、設計書は `design/` を参照してください。

| リポジトリ | 内容 |
|---|---|
| `my-app`（ここ） | API |
| `my-app-web` | 画面（Vue 3 + Vite + TypeScript） |
| `my-app-docs` | README と設計書 |

## 起動（Windows / PowerShell）

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --reload-dir app
```

API 仕様書: http://127.0.0.1:8000/docs
