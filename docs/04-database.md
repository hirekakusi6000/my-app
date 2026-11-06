# 04. DB設計

実際の定義は [migrations/0001_init.sql](../migrations/0001_init.sql)。

## テーブルの関係
```
organizations ─┬─< users ─┬─< sessions
               │          ├── profiles (1:1) ── default_seat_id → furniture
               │          ├─< user_skills >── skills
               │          ├── presence (1:1) ── seat_id → furniture
               │          └─< troubles
               ├─< positions / job_types / skills   … 候補の一覧
               └─< floors ─< rooms ─< furniture
```

## テーブル定義
| テーブル | 主なカラム | 制約・備考 |
|---|---|---|
| organizations | id, name, created_at | マスターの新規登録時に作成 |
| users | id, organization_id, email, password_hash, role, must_change_password, created_at, updated_at | email はシステム全体で重複不可（大文字・小文字を区別しない）。role は `master` / `general` |
| sessions | token_hash (PK), user_id, expires_at, created_at | トークンのハッシュ値を保存 |
| profiles | user_id (PK), name, birth_date, position_id, job_type_id, avatar_path, default_seat_id, updated_at | 行があれば初回登録済み。年齢は birth_date から計算 |
| positions | id, organization_id, name | 役職の候補 |
| job_types | id, organization_id, name, is_engineer | 職種の候補 |
| skills | id, organization_id, category, name | category は `language` / `framework` / `database` / `cloud` |
| user_skills | user_id, skill_id, years | 主キーは (user_id, skill_id)。years は 0〜50 |
| floors | id, organization_id, name, sort_order | 1組織あたり最大5 |
| rooms | id, organization_id, floor_id, name, width, height, sort_order | 1フロアあたり最大5。大きさはグリッドの単位 |
| furniture | id, organization_id, room_id, type, label, x, y, width, height, rotation | `chair` が座席。rotation は 0/90/180/270 |
| presence | user_id (PK), organization_id, status, seat_id, comment, updated_at | seat_id は UNIQUE。`present`/`away` のときだけ座席あり（CHECK 制約） |
| troubles | id, organization_id, user_id, title, body, status, created_at, updated_at | status は `open` / `resolved` |

## 共通のルール
- **組織の分離**：組織のデータを持つテーブルには `organization_id` を持たせ、repository の SQL で必ず条件に入れる。
- **削除**：ユーザーを削除すると、セッション・プロフィール・スキル・在席状態・困りごとが CASCADE で削除される。
- **座席の削除**：`presence.seat_id` は削除の連鎖をしない（NO ACTION）。座っている人がいる家具・部屋・フロアを削除するときは、先に service がその人を未出勤に戻す。DB の制約は最後の安全装置として働く。
- **日時**：UTC の ISO 8601 文字列。生年月日は `YYYY-MM-DD`。
- **真偽値**：INTEGER の 0/1（CHECK 制約付き）。
- **PRAGMA**：`foreign_keys=ON`、`journal_mode=WAL`、`busy_timeout=5000`。
- **上限**（ユーザー50・フロア5・部屋5）：service 層で確認する。
- **マイグレーション**：`migrations/NNNN_*.sql` を番号順に実行し、`PRAGMA user_version` で適用済みのバージョンを管理する。アプリの起動時に自動で実行し、`python -m app.db.migrate` で手動でも実行できる。
