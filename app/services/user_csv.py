"""ユーザーの一括登録に使う CSV の読み込み。

想定する形式（1行目は見出し）:
    メールアドレス,初期パスワード
    taro@example.com,
    hanako@example.com,my-initial-pass

- 見出しは日本語（メールアドレス / 初期パスワード）と
  英語（email / initial_password）のどちらでもよい
- 初期パスワードの列は省略でき、空欄の行はサーバーで自動生成する
- 文字コードは UTF-8（BOM あり・なし）と Shift_JIS（Excel で保存した CSV）を受け付ける
"""

import csv
import io
from dataclasses import dataclass

from app.core.errors import BusinessRuleError

MAX_CSV_BYTES = 100 * 1024
MAX_CSV_ROWS = 50

_EMAIL_HEADERS = {"email", "メールアドレス", "メール"}
_PASSWORD_HEADERS = {"initial_password", "password", "初期パスワード", "パスワード"}


@dataclass(frozen=True)
class CsvUserRow:
    line: int  # CSV ファイルの何行目か（見出しが1行目）
    email: str
    initial_password: str | None


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise BusinessRuleError(
        "CSV の文字コードを読み取れません。UTF-8 か Shift_JIS で保存してください",
        code="CSV_ENCODING",
    )


def _invalid(message: str) -> BusinessRuleError:
    return BusinessRuleError(message, code="CSV_INVALID")


def parse_user_csv(data: bytes) -> list[CsvUserRow]:
    if len(data) > MAX_CSV_BYTES:
        raise _invalid("CSV ファイルは100KBまでです")
    rows = list(csv.reader(io.StringIO(_decode(data))))
    # 空行は無視する（Excel が末尾に空行を付けることがあるため）
    numbered = [(i, r) for i, r in enumerate(rows, start=1) if any(c.strip() for c in r)]
    if not numbered:
        raise _invalid("CSV が空です")

    _, header = numbered[0]
    names = [h.strip().lower() for h in header]
    email_col = next((i for i, h in enumerate(names) if h in _EMAIL_HEADERS), None)
    password_col = next((i for i, h in enumerate(names) if h in _PASSWORD_HEADERS), None)
    if email_col is None:
        raise _invalid("1行目に「メールアドレス」の見出しが必要です")

    body = numbered[1:]
    if not body:
        raise _invalid("登録するユーザーの行がありません")
    if len(body) > MAX_CSV_ROWS:
        raise _invalid(f"一度に登録できるのは{MAX_CSV_ROWS}人までです")

    def cell(row: list[str], col: int | None) -> str:
        return row[col].strip() if col is not None and col < len(row) else ""

    return [
        CsvUserRow(
            line=line,
            email=cell(row, email_col),
            initial_password=cell(row, password_col) or None,
        )
        for line, row in body
    ]
