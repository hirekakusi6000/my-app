"""画面の JavaScript に文法エラーがないことを確認する（Node.js があるときだけ実行）。

画面のスクリプトは ES モジュールなので、拡張子 .mjs の一時ファイルにコピーしてから
`node --check` で文法だけを確認する（実行はしない）。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js がインストールされていません")


def test_all_scripts_have_valid_syntax(tmp_path):
    scripts = sorted(FRONTEND.rglob("*.js"))
    assert scripts, "画面のスクリプトが見つかりません"

    errors = []
    for script in scripts:
        copy = tmp_path / "check.mjs"
        shutil.copyfile(script, copy)
        result = subprocess.run(
            [NODE, "--check", str(copy)], capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            message = result.stderr.strip().splitlines()
            errors.append(f"{script.relative_to(FRONTEND)}: {' / '.join(message[:4])}")
    assert not errors, "文法エラーがあります:\n" + "\n".join(errors)
