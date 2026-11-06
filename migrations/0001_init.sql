-- 0001: 初期スキーマ
-- 日時は UTC の ISO 8601 文字列、真偽値は 0/1 の INTEGER で保存する。
-- 組織のデータを持つテーブルには organization_id を持たせ、repository で必ず絞り込む。

-- ───────── 組織・ユーザー・認証 ─────────

CREATE TABLE organizations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
    created_at  TEXT    NOT NULL
);

CREATE TABLE users (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id       INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email                 TEXT    NOT NULL COLLATE NOCASE UNIQUE CHECK (length(email) BETWEEN 3 AND 254),
    password_hash         TEXT    NOT NULL,
    role                  TEXT    NOT NULL CHECK (role IN ('master', 'general')),
    must_change_password  INTEGER NOT NULL DEFAULT 0 CHECK (must_change_password IN (0, 1)),
    created_at            TEXT    NOT NULL,
    updated_at            TEXT    NOT NULL
);
CREATE INDEX ix_users_organization_id ON users(organization_id);

CREATE TABLE sessions (
    token_hash  TEXT    PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
CREATE INDEX ix_sessions_user_id ON sessions(user_id);
CREATE INDEX ix_sessions_expires_at ON sessions(expires_at);

-- ───────── 候補の一覧（役職・職種・スキル） ─────────

CREATE TABLE positions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name             TEXT    NOT NULL COLLATE NOCASE CHECK (length(name) BETWEEN 1 AND 50),
    UNIQUE (organization_id, name)
);

CREATE TABLE job_types (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name             TEXT    NOT NULL COLLATE NOCASE CHECK (length(name) BETWEEN 1 AND 50),
    is_engineer      INTEGER NOT NULL DEFAULT 0 CHECK (is_engineer IN (0, 1)),
    UNIQUE (organization_id, name)
);

CREATE TABLE skills (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    category         TEXT    NOT NULL CHECK (category IN ('language', 'framework', 'database', 'cloud')),
    name             TEXT    NOT NULL COLLATE NOCASE CHECK (length(name) BETWEEN 1 AND 50),
    UNIQUE (organization_id, category, name)
);

-- ───────── オフィス（フロア・部屋・家具） ─────────

CREATE TABLE floors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name             TEXT    NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    sort_order       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (organization_id, name)
);

CREATE TABLE rooms (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    floor_id         INTEGER NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
    name             TEXT    NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    width            INTEGER NOT NULL CHECK (width BETWEEN 5 AND 200),
    height           INTEGER NOT NULL CHECK (height BETWEEN 5 AND 200),
    sort_order       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (floor_id, name)
);
CREATE INDEX ix_rooms_organization_id ON rooms(organization_id);

-- type = 'chair' の家具が座席になる。座標・大きさはグリッドの単位
CREATE TABLE furniture (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    room_id          INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    type             TEXT    NOT NULL CHECK (type IN ('desk', 'chair', 'wall', 'door', 'other')),
    label            TEXT    CHECK (label IS NULL OR length(label) <= 50),
    x                INTEGER NOT NULL CHECK (x >= 0),
    y                INTEGER NOT NULL CHECK (y >= 0),
    width            INTEGER NOT NULL CHECK (width >= 1),
    height           INTEGER NOT NULL CHECK (height >= 1),
    rotation         INTEGER NOT NULL DEFAULT 0 CHECK (rotation IN (0, 90, 180, 270))
);
CREATE INDEX ix_furniture_room_id ON furniture(room_id);

-- ───────── プロフィール・スキル ─────────

CREATE TABLE profiles (
    user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name             TEXT    NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    birth_date       TEXT    NOT NULL CHECK (birth_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    position_id      INTEGER REFERENCES positions(id) ON DELETE SET NULL,
    job_type_id      INTEGER REFERENCES job_types(id) ON DELETE SET NULL,
    avatar_path      TEXT,
    default_seat_id  INTEGER REFERENCES furniture(id) ON DELETE SET NULL,
    updated_at       TEXT    NOT NULL
);

CREATE TABLE user_skills (
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id  INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    years     INTEGER NOT NULL CHECK (years BETWEEN 0 AND 50),
    PRIMARY KEY (user_id, skill_id)
);
CREATE INDEX ix_user_skills_skill_id ON user_skills(skill_id);

-- ───────── 出勤・在席 ─────────

-- seat_id は UNIQUE（同じ座席に2人座れない）。NULL は複数行あってよい。
-- 座っている人がいる家具の削除は DB では拒否される（NO ACTION）。service が先に座席を空ける。
CREATE TABLE presence (
    user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    status           TEXT    NOT NULL DEFAULT 'not_working'
                     CHECK (status IN ('not_working', 'present', 'away', 'remote')),
    seat_id          INTEGER UNIQUE REFERENCES furniture(id),
    comment          TEXT    CHECK (comment IS NULL OR length(comment) <= 100),
    updated_at       TEXT    NOT NULL,
    -- 在席中・離席中のときだけ座席を持つ
    CHECK ((status IN ('present', 'away')) = (seat_id IS NOT NULL))
);
CREATE INDEX ix_presence_organization_id ON presence(organization_id);

-- ───────── 困りごと ─────────

CREATE TABLE troubles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id  INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title            TEXT    NOT NULL CHECK (length(title) BETWEEN 1 AND 100),
    body             TEXT    NOT NULL DEFAULT '' CHECK (length(body) <= 2000),
    status           TEXT    NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL
);
CREATE INDEX ix_troubles_organization_status ON troubles(organization_id, status);
CREATE INDEX ix_troubles_user_id ON troubles(user_id);
