"""主な利用の流れを、本物のブラウザで最初から最後まで操作して確認する。"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import MASTER_EMAIL, MASTER_PASSWORD, login

pytestmark = pytest.mark.e2e

CELL = 32  # マップの1マスの大きさ（px）


# ───────── マスター ─────────


def test_master_signs_up_and_creates_sample(page: Page, app_url, console_errors):
    page.goto(f"{app_url}/signup.html")
    page.get_by_label("組織名").fill("テスト株式会社")
    page.get_by_label("メールアドレス").fill(MASTER_EMAIL)
    page.locator('[name="password"]').fill(MASTER_PASSWORD)
    page.locator('[name="password_confirm"]').fill(MASTER_PASSWORD)
    page.get_by_role("button", name="登録する").click()

    # 新規登録するとユーザー管理画面に移り、サンプルの案内が出る
    expect(page).to_have_url(f"{app_url}/admin/users.html")
    expect(page.locator(".app-header__brand")).to_have_text("テスト株式会社")
    page.get_by_role("button", name="サンプルを作成").click()
    expect(page.locator("#user-rows tr")).to_have_count(7)  # マスター＋サンプルの6人

    # マップには在席中・離席中の4人が表示される
    page.get_by_role("link", name="マップ", exact=True).click()
    expect(page.locator(".occupant")).to_have_count(4)
    page.get_by_role("button", name="山田 太郎（在席中）").click()
    popup = page.locator(".profile-popup")
    expect(popup.locator("[data-name]")).to_have_text("山田 太郎")
    expect(popup).to_contain_text("Python 10年")

    assert console_errors == []


def test_all_pages_load_without_errors(page: Page, app_url, with_sample, console_errors):
    """CSP の制限の下でも、すべての画面がエラーなく表示されること。"""
    login(page, app_url, MASTER_EMAIL, MASTER_PASSWORD)
    checks = {
        "/map.html": ".occupant",
        "/people.html": ".person-card",
        "/admin/users.html": "#user-rows tr",
        "/admin/offices.html": "#floors .panel",
        "/admin/map-editor.html": ".furniture",
        "/admin/seats.html": "#rows tr",
        "/admin/master-data.html": "#item-list li",
        "/admin/organization.html": "#rename-form",
    }
    for path, selector in checks.items():
        page.goto(f"{app_url}{path}")
        expect(page.locator(selector).first).to_be_visible()
    assert console_errors == []


def test_csv_import(page: Page, app_url, api, console_errors):
    login(page, app_url, MASTER_EMAIL, MASTER_PASSWORD)
    page.get_by_role("button", name="CSV で一括登録").click()
    csv = (
        "メールアドレス,初期パスワード\r\ntaro@example.com,\r\nhanako@example.com,hanako-pass-1\r\n"
    )
    page.locator("#import-dialog [data-file]").set_input_files(
        {"name": "users.csv", "mimeType": "text/csv", "buffer": csv.encode("utf-8")}
    )
    dialog = page.locator("#import-dialog")
    expect(dialog.locator("[data-summary]")).to_contain_text("2人を登録できます")
    dialog.get_by_role("button", name="登録する").click()
    expect(dialog.locator("[data-summary]")).to_contain_text("2人を登録しました")
    expect(dialog.get_by_role("button", name="結果を CSV で保存")).to_be_visible()
    expect(page.locator("#user-rows tr")).to_have_count(3)
    assert console_errors == []


# ───────── 従業員 ─────────


def test_employee_first_login_check_in_and_out(page: Page, app_url, with_sample, console_errors):
    res = with_sample.post(
        "/users", json={"email": "newcomer@example.com", "initial_password": "initial-pass-1"}
    )
    assert res.status_code == 201

    # 初回ログイン → パスワード変更 → プロフィール登録 → デフォルト座席（後で）→ マップ
    login(page, app_url, "newcomer@example.com", "initial-pass-1")
    expect(page).to_have_url(f"{app_url}/setup.html")
    page.get_by_label("現在のパスワード（初期パスワード）").fill("initial-pass-1")
    page.locator('[name="new_password"]').fill("my-new-pass-1")
    page.locator('[name="new_password_confirm"]').fill("my-new-pass-1")
    page.get_by_role("button", name="変更して次へ").click()

    page.get_by_label("名前").fill("新人 花子")
    page.get_by_label("生年月日").fill("1998-05-10")
    page.get_by_label("職種").fill("営業")
    page.get_by_role("button", name="登録して次へ").click()
    page.get_by_role("link", name="はじめる").click()
    expect(page).to_have_url(f"{app_url}/map.html")
    expect(page.locator("#my-badge")).to_have_text("未出勤")

    # 出社：空いている椅子 A-3 を選んで出社する
    page.get_by_role("button", name="出社", exact=True).click()
    page.locator(".furniture--chair", has_text="A-3").click()
    page.get_by_role("button", name="この座席で出社").click()
    expect(page.locator("#my-badge")).to_have_text("在席中")
    expect(page.locator("#my-seat")).to_contain_text("A-3")
    expect(page.locator(".occupant")).to_have_count(5)

    # 離席 → 在席に戻る → 退勤
    page.get_by_role("button", name="離席", exact=True).click()
    expect(page.locator("#my-badge")).to_have_text("離席中")
    page.get_by_role("button", name="在席に戻る", exact=True).click()
    expect(page.locator("#my-badge")).to_have_text("在席中")
    page.get_by_role("button", name="退勤", exact=True).click()
    expect(page.locator("#my-badge")).to_have_text("未出勤")
    expect(page.locator(".occupant")).to_have_count(4)

    assert console_errors == []


def test_cannot_take_occupied_seat(page: Page, app_url, with_sample, console_errors):
    with_sample.post("/users", json={"email": "u@example.com", "initial_password": "initial-1"})
    login(page, app_url, "u@example.com", "initial-1")
    page.get_by_label("現在のパスワード（初期パスワード）").fill("initial-1")
    page.locator('[name="new_password"]').fill("my-new-pass-1")
    page.locator('[name="new_password_confirm"]').fill("my-new-pass-1")
    page.get_by_role("button", name="変更して次へ").click()
    page.get_by_label("名前").fill("新人")
    page.get_by_label("生年月日").fill("1998-05-10")
    page.get_by_role("button", name="登録して次へ").click()
    page.get_by_role("link", name="はじめる").click()

    # 山田さんが座っている A-1 は選べない
    page.get_by_role("button", name="出社", exact=True).click()
    page.locator(".furniture--chair", has_text="A-1").click(force=True)
    expect(page.locator(".toast--error")).to_have_text("この座席は使用中です")
    expect(page.get_by_role("button", name="この座席で出社")).to_be_disabled()
    assert console_errors == []


# ───────── マップ編集・メンバー検索 ─────────


def test_map_editor_select_duplicate_undo_and_save(
    page: Page, app_url, with_sample, console_errors
):
    login(page, app_url, MASTER_EMAIL, MASTER_PASSWORD)
    page.goto(f"{app_url}/admin/map-editor.html")
    furniture = page.locator(".furniture")
    expect(furniture).to_have_count(18)

    # 何もない所からドラッグして、机の島A（机1＋椅子6）を範囲選択する
    box = page.locator(".room-map").bounding_box()
    page.mouse.move(box["x"] + 1.2 * CELL, box["y"] + 2.5 * CELL)
    page.mouse.down()
    page.mouse.move(box["x"] + 8.6 * CELL, box["y"] + 7.4 * CELL, steps=5)
    page.mouse.up()
    expect(page.locator(".furniture--selected")).to_have_count(7)
    expect(page.locator("#props [data-type]")).to_have_text("7個を選択中")

    # 複製 → 元に戻す → やり直す
    page.keyboard.press("Control+d")
    expect(furniture).to_have_count(25)
    page.keyboard.press("Control+z")
    expect(furniture).to_have_count(18)
    page.keyboard.press("Control+y")
    expect(furniture).to_have_count(25)

    # 保存すると、サーバーにも25個が保存される
    page.get_by_role("button", name="保存する").click()
    expect(page.locator("#status")).to_have_text("保存済み")
    room_id = with_sample.get("/floors").json()[0]["rooms"][0]["id"]
    assert len(with_sample.get(f"/rooms/{room_id}/layout").json()["furniture"]) == 25
    assert console_errors == []


def test_people_search_and_show_on_map(page: Page, app_url, with_sample, console_errors):
    login(page, app_url, MASTER_EMAIL, MASTER_PASSWORD)
    page.goto(f"{app_url}/people.html")
    expect(page.locator(".person-card")).to_have_count(6)

    skill = page.get_by_placeholder("例：Python")
    skill.fill("python")
    skill.press("Enter")
    cards = page.locator(".person-card")
    expect(cards).to_have_count(2)
    expect(cards.locator(".chip--matched")).to_have_count(2)

    cards.filter(has_text="山田 太郎").get_by_role("link").click()
    expect(page).to_have_url(re.compile(r"/map\.html\?room=\d+&seat=\d+$"))
    expect(page.locator(".occupant--focus")).to_have_count(1)
    assert console_errors == []
