"""クラスの中の型注釈が、同じクラスのメソッド名に隠されていないことを確認する。

例：list というメソッドを定義した後で list[int] と書くと、Python 3.12・3.13 では
組み込みの list ではなくそのメソッドを指し、読み込み時にエラーになる。
（開発で使っている 3.14 は型注釈をすぐには評価しないので、気付きにくい）
`from __future__ import annotations` を書いたファイルは、型注釈を評価しないので対象外。
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"


def _shadowed_annotations(source: str) -> list[str]:
    tree = ast.parse(source)
    if any(
        isinstance(n, ast.ImportFrom)
        and n.module == "__future__"
        and any(a.name == "annotations" for a in n.names)
        for n in tree.body
    ):
        return []
    problems = []
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        defined: set[str] = set()
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            args = item.args.posonlyargs + item.args.args + item.args.kwonlyargs
            annotations = [a.annotation for a in args if a.annotation] + [item.returns]
            for annotation in filter(None, annotations):
                for node in ast.walk(annotation):
                    if isinstance(node, ast.Name) and node.id in defined:
                        problems.append(f"{cls.name}.{item.name} の型注釈の {node.id}")
            defined.add(item.name)
    return problems


def test_no_annotation_is_shadowed_by_a_method_name():
    problems = {
        str(path.relative_to(APP)): found
        for path in APP.rglob("*.py")
        if (found := _shadowed_annotations(path.read_text(encoding="utf-8")))
    }
    assert problems == {}


def test_detects_shadowing():
    source = (
        "class Repo:\n"
        "    def list(self) -> None: ...\n"
        "    def replace(self, items: list[int]) -> None: ...\n"
    )
    assert _shadowed_annotations(source) == ["Repo.replace の型注釈の list"]
    assert _shadowed_annotations("from __future__ import annotations\n" + source) == []
