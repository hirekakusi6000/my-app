from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_returns_ok(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_unknown_api_returns_error_format(client):
    res = client.get("/api/v1/does-not-exist")
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_frontend_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


# ───────── 画面ファイルの配信（web/dist → frontend/ の順に探す） ─────────


def _frontend_settings(tmp_path, *, with_dist: bool = True) -> Settings:
    legacy = tmp_path / "frontend"
    (legacy / "admin").mkdir(parents=True)
    (legacy / "index.html").write_text("legacy-index", encoding="utf-8")
    (legacy / "admin" / "organization.html").write_text("legacy-org", encoding="utf-8")
    dist = tmp_path / "dist"
    if with_dist:
        (dist / "admin").mkdir(parents=True)
        (dist / "admin" / "organization.html").write_text("vue-org", encoding="utf-8")
    return Settings(
        _env_file=None,
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
        frontend_dir=legacy,
        web_dist_dir=dist,
    )


def test_vue_build_is_served_before_legacy_files(tmp_path):
    with TestClient(create_app(_frontend_settings(tmp_path))) as c:
        res = c.get("/admin/organization.html")
        assert res.text == "vue-org"
        assert res.headers["cache-control"] == "no-cache"
        # Vue に移行していない画面は frontend/ から配信する
        assert c.get("/").text == "legacy-index"
        assert c.get("/missing.html").status_code == 404


def test_legacy_files_are_served_without_vue_build(tmp_path, capsys):
    with TestClient(create_app(_frontend_settings(tmp_path, with_dist=False))) as c:
        assert c.get("/admin/organization.html").text == "legacy-org"
    # ビルドし忘れに気付けるよう、起動時に警告を出す（app のログは標準エラーに出る）
    assert "npm run build" in capsys.readouterr().err
