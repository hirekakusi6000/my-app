import pytest

from app.core.errors import BusinessRuleError
from app.services.user_csv import MAX_CSV_ROWS, parse_user_csv


def _rows(text: str, encoding: str = "utf-8"):
    return [(r.line, r.email, r.initial_password) for r in parse_user_csv(text.encode(encoding))]


def test_japanese_header_and_optional_password():
    text = "メールアドレス,初期パスワード\ntaro@example.com,\nhanako@example.com,pass-1234\n"
    assert _rows(text) == [
        (2, "taro@example.com", None),
        (3, "hanako@example.com", "pass-1234"),
    ]


def test_english_header_without_password_column():
    assert _rows("email\n a@example.com \n") == [(2, "a@example.com", None)]


def test_columns_can_be_in_any_order_and_blank_lines_are_ignored():
    text = "初期パスワード,メモ,メールアドレス\n\npw-123456,営業,a@example.com\n\n"
    assert _rows(text) == [(3, "a@example.com", "pw-123456")]


def test_utf8_with_bom():
    assert _rows("﻿メールアドレス\na@example.com\n") == [(2, "a@example.com", None)]


def test_shift_jis_from_excel():
    text = "メールアドレス,初期パスワード\r\na@example.com,\r\n"
    assert _rows(text, encoding="cp932") == [(2, "a@example.com", None)]


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"", "CSV_INVALID"),
        ("名前\n山田\n".encode(), "CSV_INVALID"),  # メールアドレスの見出しがない
        ("メールアドレス\n".encode(), "CSV_INVALID"),  # データ行がない
        (b"email\n" + b"a@example.com\n" * (MAX_CSV_ROWS + 1), "CSV_INVALID"),
        (b"email\n" + b"x" * 200_000, "CSV_INVALID"),  # 100KB を超える
        (b"\xff\xfe\x00\x00\x81", "CSV_ENCODING"),
    ],
)
def test_invalid_files(data, code):
    with pytest.raises(BusinessRuleError) as exc:
        parse_user_csv(data)
    assert exc.value.code == code
