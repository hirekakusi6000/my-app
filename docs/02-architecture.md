# 02. システムアーキテクチャ

## 全体の構成
```
[ブラウザ (PC)]  HTML / CSS / JS (ES Modules)、マップは SVG で描画
   │  fetch (JSON) ＋ セッション Cookie、30秒ごとのポーリング
   ▼
[Uvicorn]
   ▼
[FastAPI]
 ├─ /               → 画面ファイル (frontend/)
 ├─ /api/v1/...     → Router     … HTTP の処理、入力チェック (Pydantic)
 │                      │  Depends: ログイン中ユーザー / 権限 / 初回設定済みか
 │                      ▼
 │                   Service    … 業務ルール、トランザクション
 │                      ▼
 │                   Repository … 生SQL (sqlite3、プレースホルダー必須、organization_id で絞り込み)
 │                      ▼
 └───────────────── SQLite (data/app.db)  ＋  data/uploads/ (プロフィール画像)
```

依存の向きは `api → services → repositories → db` の一方向だけ。上の層は下の層だけを呼び出す。

## 認証・認可
| 項目 | 方式 |
|---|---|
| パスワード | Argon2 でハッシュ化（`argon2-cffi`） |
| セッション | ランダムなトークンを Cookie に入れる（`HttpOnly`、`SameSite=Lax`、本番では `Secure`）。DB にはトークンの SHA-256 ハッシュを保存 |
| CSRF 対策 | `SameSite=Lax` に加え、データを変更する API は JSON の送信だけを受け付ける |
| 権限チェック | Depends で `get_current_user` → `require_master` / `require_general` / `require_setup_completed` |
| 組織の分離 | repository のすべての SQL で `organization_id` を条件にする。他の組織のデータは 404 を返す |
| 回数制限 | 新規登録：同じIPから1時間に5回、ログイン：同じIP＋メールで5分に10回（メモリ上でカウント） |

## 在席状態
| 状態 (status) | 意味 | 座席 |
|---|---|---|
| `not_working` | 未出勤 | なし |
| `present` | 在席中 | あり |
| `away` | 離席中 | あり（確保したまま） |
| `remote` | リモート | なし |

同じ座席に2人が座れないように、座席の列に UNIQUE 制約を付ける。同時に同じ座席を選んだ場合も DB が片方を拒否し、その人には 409 `SEAT_OCCUPIED` を返す。

## エラーの形式
```json
{ "detail": "この座席は使用中です", "code": "SEAT_OCCUPIED" }
```
service は業務エラー（`AppError` を継承したクラス）を投げ、`app/core/errors.py` の例外ハンドラーが HTTP のステータスに変換する。

## 設定（.env、接頭辞 `APP_`）
| 変数 | 既定値 | 内容 |
|---|---|---|
| `APP_DATABASE_PATH` | `data/app.db` | SQLite ファイルの場所 |
| `APP_UPLOAD_DIR` | `data/uploads` | プロフィール画像の保存先 |
| `APP_SESSION_EXPIRE_HOURS` | `168` | セッションの有効期限（時間） |
| `APP_COOKIE_SECURE` | `false` | 本番（HTTPS）では `true` |

## テストの方針
- service の単体テスト（テストごとに一時DBを作る）
- API の結合テスト（`TestClient`、マスターと一般ユーザーの fixture）
- 重点的に確認する点：権限、**組織をまたいだアクセス**、座席の重複、初回設定への誘導、入力チェック
