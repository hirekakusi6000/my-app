"""画面の自動テスト（Playwright）の共通の準備。

テストごとに、一時フォルダの DB を使うアプリを別スレッドの Uvicorn で起動し、
本物のブラウザ（Chromium、画面なし）で操作する。テストごとにアプリを作り直すので、
新規登録の回数制限やデータが他のテストに影響しない。
"""

import socket
import threading
import time
from collections.abc import Iterator

import httpx
import pytest
import uvicorn
from playwright.sync_api import Page

from app.core.config import Settings
from app.main import create_app

MASTER_EMAIL = "master@example.com"
MASTER_PASSWORD = "master-pass-123"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def app_url(tmp_path) -> Iterator[str]:
    """テスト用のアプリを起動し、その URL を返す。"""
    settings = Settings(
        _env_file=None,
        database_path=tmp_path / "e2e.db",
        upload_dir=tmp_path / "uploads",
        log_level="ERROR",
    )
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(settings),
            host="127.0.0.1",
            port=port,
            log_level="error",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("テスト用のサーバーが起動しませんでした")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    # 画面は PC 向け（幅 1280px 以上）なので、広めの画面で操作する
    return {**browser_context_args, "viewport": {"width": 1400, "height": 900}, "locale": "ja-JP"}


@pytest.fixture
def console_errors(page: Page) -> list[str]:
    """ブラウザのコンソールのエラーと、画面のスクリプトの例外を集める。

    ログイン前の状態確認（GET /me）が 401 を返すのは正常な動きなので除く。
    CSP に違反した読み込みもコンソールのエラーとして記録される。
    """
    errors: list[str] = []
    page.on(
        "console",
        lambda m: m.type == "error" and "status of 401" not in m.text and errors.append(m.text),
    )
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    # confirm() などの確認ダイアログは「OK」を押したことにする
    page.on("dialog", lambda d: d.accept())
    return errors


@pytest.fixture
def api(app_url) -> Iterator[httpx.Client]:
    """テストの準備（データの作成など）に使う API クライアント。マスターとしてログイン済み。"""
    with httpx.Client(base_url=f"{app_url}/api/v1") as client:
        res = client.post(
            "/auth/signup",
            json={
                "organization_name": "テスト株式会社",
                "email": MASTER_EMAIL,
                "password": MASTER_PASSWORD,
            },
        )
        assert res.status_code == 201, res.text
        yield client


@pytest.fixture
def with_sample(api) -> httpx.Client:
    """お試し用のサンプル（オフィスマップと従業員6人）を作成済みの組織。"""
    assert api.post("/organization/sample-data").status_code == 201
    return api


def login(page: Page, app_url: str, email: str, password: str) -> None:
    """ログイン画面から実際にログインする。"""
    page.goto(f"{app_url}/login.html")
    page.get_by_label("メールアドレス").fill(email)
    page.locator('[name="password"]').fill(password)
    page.get_by_role("button", name="ログイン").click()
    page.wait_for_url(lambda url: "/login.html" not in url)
