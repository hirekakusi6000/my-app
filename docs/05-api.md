# 05. API設計

## 共通ルール
- ベースURL：`/api/v1`。JSON でやり取りする（プロフィール画像だけ multipart）
- 認証：セッション Cookie
- エラー：`{"detail": "...", "code": "..."}`

| HTTP | 使う場面 | code の例 |
|---|---|---|
| 401 | ログインしていない、セッション切れ | `UNAUTHENTICATED` |
| 403 | 権限がない、初回設定が終わっていない | `FORBIDDEN`, `SETUP_REQUIRED` |
| 404 | データがない（他の組織のデータも 404） | `NOT_FOUND` |
| 409 | 競合 | `SEAT_OCCUPIED`, `EMAIL_TAKEN` |
| 422 | 入力値のエラー、上限を超えた | `VALIDATION_ERROR`, `LIMIT_EXCEEDED` |
| 429 | 試行回数の制限を超えた | `RATE_LIMITED` |

**初回設定中に使える API**：パスワード変更前は `/me`、`/me/password`、`/auth/logout` だけ。パスワード変更後、プロフィール登録までは、それに加えてプロフィール・スキル・画像の登録、候補の一覧の取得、フロアと配置の取得が使える。

## 認証・自分の情報
| メソッド | パス | 権限 | 内容 |
|---|---|---|---|
| POST | `/auth/signup` | 公開（回数制限あり） | 組織名・メール・パスワードを受け取り、組織とマスターを作ってログイン |
| POST | `/auth/login` | 公開（回数制限あり） | ログイン |
| POST | `/auth/logout` | ログイン中 | ログアウト |
| GET | `/me` | ログイン中 | 権限、組織、`must_change_password`、`profile_completed` |
| PUT | `/me/password` | ログイン中 | パスワード変更 |

## ユーザー管理（マスター）
| メソッド | パス | 内容 |
|---|---|---|
| GET | `/users` | 組織のユーザー一覧 |
| POST | `/users` | 一般ユーザーを作成（上限50名） |
| PATCH | `/users/{id}` | メールアドレスの変更 |
| POST | `/users/{id}/password-reset` | パスワードのリセット（次のログインで変更を強制） |
| DELETE | `/users/{id}` | 物理削除（自分自身は削除できない） |

## プロフィール・スキル
| メソッド | パス | 権限 | 内容 |
|---|---|---|---|
| GET / PUT | `/me/profile` | 一般 | 名前・生年月日・役職・職種・デフォルト座席。候補にない名前は自動で追加 |
| PUT | `/me/skills` | 一般 | スキルをまとめて置き換える |
| PUT / DELETE | `/me/avatar` | 一般 | プロフィール画像（PNG / JPEG / WebP、2MB以下） |
| GET | `/profiles/{user_id}` | 全員 | プロフィールと勤務状況 |
| GET | `/users/{id}/avatar` | 全員 | 画像そのもの |

## 候補の一覧
| メソッド | パス | 権限 |
|---|---|---|
| GET | `/positions`, `/job-types`, `/skills?category=` | 全員 |
| POST / PATCH / DELETE | 上の3つの一覧の追加・変更・削除 | マスター |

## オフィス
| メソッド | パス | 権限 | 内容 |
|---|---|---|---|
| GET | `/floors` | 全員 | フロアと部屋の一覧 |
| POST / PATCH / DELETE | `/floors`, `/floors/{id}` | マスター | |
| POST | `/floors/{id}/rooms` | マスター | |
| PATCH / DELETE | `/rooms/{id}` | マスター | |
| GET | `/rooms/{id}/layout` | 全員 | 部屋と家具の一覧 |
| PUT | `/rooms/{id}/layout` | マスター | 配置をまとめて保存（更新・作成・削除） |
| GET | `/rooms/{id}/occupancy` | 全員 | 座席ごとに座っている人と状態 |

## 出勤・在席
| メソッド | パス | 権限 | 内容 |
|---|---|---|---|
| GET | `/me/presence` | 一般 | 自分の状態 |
| PUT | `/me/presence` | 一般 | `{status, seat_id, comment}`。使用中の座席なら 409 |
| GET | `/presence` | 全員 | 組織全員の状態の一覧 |
| DELETE | `/seats/{seat_id}/occupant` | マスター | 座席を強制的に空ける |

## 困りごと
| メソッド | パス | 権限 |
|---|---|---|
| GET | `/troubles?status=` | 全員 |
| POST | `/troubles` | 一般 |
| PATCH | `/troubles/{id}` | 登録した本人 |
| DELETE | `/troubles/{id}` | 本人・マスター |

## 動作確認用
| メソッド | パス | 内容 |
|---|---|---|
| GET | `/health` | サーバーと DB の動作確認 |
