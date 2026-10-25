# SPDX-License-Identifier: Apache-2.0
"""The reference model, the reference evaluator of tables beside it, the build's models (the declaration's
own check and the results) and their direct checks import nothing from `materica`, at any depth, so that they
never rest on the code they check: neither by the imports their source writes, followed through the modules
beside them, nor in a fresh interpreter that imports them. The
control is a throwaway package whose first module reaches `materica` only through its second, and another is
the evaluator's own source with one import of the core added; both checks must see both."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
MODEL = (
    "tests.reference.read_model",
    "tests.reference.strict_json",
    "tests.reference.table_evaluator",
    "tests.reference.build_model",
    "tests.reference.direct",
    "tests.reference.build_results_model",
)


def module_file(module: str, root: Path) -> Path | None:
    """The file under `root` for `module`, or None for a module from elsewhere."""
    base = root.joinpath(*module.split("."))
    for path in (base.with_suffix(".py"), base / "__init__.py"):
        if path.is_file():
            return path
    return None


def imported(module: str, root: Path = REPOSITORY) -> set[str]:
    """Every module importing `module` loads, its packages' and the imports of every module under `root`
    followed to any depth; `from a import b` loads `a`, and `a.b` where that is a module."""
    found: set[str] = set()
    pending = [module]
    while pending:
        parts = pending.pop().split(".")
        for name in (".".join(parts[: end + 1]) for end in range(len(parts))):
            if name in found:
                continue
            found.add(name)
            path = module_file(name, root)
            if path is not None:
                pending.extend(imports_written(path, name, root))
    return found


def imports_written(path: Path, module: str, root: Path) -> list[str]:
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    written: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            written.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                anchor = parts[: len(parts) - (node.level - 1)]
                base = ".".join([*anchor, *([base] if base else [])])
            written.append(base)
            written.extend(
                f"{base}.{alias.name}" for alias in node.names if module_file(f"{base}.{alias.name}", root)
            )
    return written


def loaded_in_a_fresh_interpreter(module: str, root: Path = REPOSITORY) -> list[str]:
    """The `materica` modules a fresh, isolated interpreter holds once it has imported `module`."""
    probe = "\n".join(
        [
            "import importlib, sys",
            f"sys.path.insert(0, {str(root)!r})",
            f"importlib.import_module({module!r})",
            "print(*sorted(name for name in sys.modules if name.partition('.')[0] == 'materica'))",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", probe], capture_output=True, text=True, check=True, cwd=root
    )
    return completed.stdout.split()


def from_materica(modules: set[str] | list[str]) -> list[str]:
    return sorted(module for module in modules if module.partition(".")[0] == "materica")


@pytest.mark.parametrize("module", MODEL)
def test_the_model_writes_no_import_that_reaches_materica(module: str) -> None:
    assert from_materica(imported(module)) == []


@pytest.mark.parametrize("module", MODEL)
def test_the_model_loads_no_materica_module(module: str) -> None:
    assert loaded_in_a_fresh_interpreter(module) == []


def test_both_checks_see_materica_reached_through_another_module(tmp_path: Path) -> None:
    package = tmp_path / "throwaway"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "first.py").write_text("from . import second\n")
    (package / "second.py").write_text("from materica.core.jsonio import JsonValue\n")
    assert "throwaway.second" in imported("throwaway.first", tmp_path)
    assert "materica.core.jsonio" in from_materica(imported("throwaway.first", tmp_path))
    assert "materica.core.jsonio" in loaded_in_a_fresh_interpreter("throwaway.first", tmp_path)


def test_the_walk_resolves_relative_imports(tmp_path: Path) -> None:
    source = tmp_path / "relative.py"
    source.write_text("from . import strict_json\nfrom .strict_json import parse\nfrom .. import conftest\n")
    assert imports_written(source, "tests.reference.relative", REPOSITORY) == [
        "tests.reference",
        "tests.reference.strict_json",
        "tests.reference.strict_json",
        "tests",
        "tests.conftest",
    ]


def test_an_import_of_materica_added_to_the_evaluator_is_seen_by_both_checks(tmp_path: Path) -> None:
    """The evaluator's own source, with one import of the core added, in a copy of its package."""
    package = tmp_path / "tests" / "reference"
    package.mkdir(parents=True)
    (tmp_path / "tests" / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    source = (REPOSITORY / "tests" / "reference" / "table_evaluator.py").read_text(encoding="utf-8")
    assert from_materica(imported("tests.reference.table_evaluator", REPOSITORY)) == []
    (package / "table_evaluator.py").write_text(source + "\nfrom materica.core.jsonio import JsonValue\n")
    assert "materica.core.jsonio" in from_materica(imported("tests.reference.table_evaluator", tmp_path))
    assert "materica.core.jsonio" in loaded_in_a_fresh_interpreter(
        "tests.reference.table_evaluator", tmp_path
    )
