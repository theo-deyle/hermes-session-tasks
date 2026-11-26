"""Layout, import and home guards for the plugin tree.

Each guard is a helper that takes a directory and returns findings. Each helper has
one self-test that proves it reports a bad module. The tree test then proves that
`plugin/` has no findings.
"""

from __future__ import annotations

import ast
import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from home_guard import new_entries, snapshot

pytest_plugins = ["pytester"]

TESTS_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = TESTS_DIR.parent / "plugin"
CORE_DIR = PLUGIN_DIR / "session_tasks"

MANIFEST_NAMES = frozenset({
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
    "environment.yml",
    "package.json",
    "package-lock.json",
})
HERMES_PUBLIC_IMPORTS = (
    "plugins.plugin_storage",
    "hermes_state",
    "hermes_constants",
    "hermes_cli.plugin_events",
)
MAX_MODULE_LINES = 500
DASHBOARD_THIRD_PARTY = frozenset({"fastapi", "pydantic"})
ARGUMENT_NAMES = frozenset({"args", "function_args"})
ARGUMENT_READERS = frozenset({"get", "pop"})
FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
# The one read of `session_id` from the tool arguments that D-38 allows: it only names a
# board to read. Pairs of (file name, function name).
SANCTIONED_ARG_READS = frozenset({("copy_args.py", "read_target")})
# The session id limit has one literal home, so the tool parser and the routes cannot drift (D-56).
SESSION_ID_LIMIT_NAME = "SESSION_ID_MAX"
SESSION_ID_LIMIT_HOME = "session_tasks/copy_args.py"


def _python_files(directory: Path) -> list[Path]:
    return sorted(directory.rglob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _finding(path: Path, node: ast.AST, message: str) -> str:
    return f"{path.name}:{getattr(node, 'lineno', 0)}: {message}"


def _walk_outside_functions(node: ast.AST) -> Iterator[ast.AST]:
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, FUNCTION_NODES):
            yield from _walk_outside_functions(child)


def _imported_modules(node: ast.AST) -> list[str]:
    """Absolute module names that an import statement names. Relative imports give none."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module]
    return []


def _is_stdlib(module: str) -> bool:
    return module.split(".")[0] in sys.stdlib_module_names


def _is_public_hermes(module: str) -> bool:
    return any(module == name or module.startswith(name + ".") for name in HERMES_PUBLIC_IMPORTS)


def manifest_findings(plugin_dir: Path) -> list[str]:
    return sorted(
        path.relative_to(plugin_dir).as_posix()
        for path in plugin_dir.rglob("*")
        if path.is_file() and (path.name in MANIFEST_NAMES or path.name.startswith("requirements"))
    )


def module_level_import_findings(core_dir: Path) -> list[str]:
    findings: list[str] = []
    for path in _python_files(core_dir):
        for node in _walk_outside_functions(_parse(path)):
            for module in _imported_modules(node):
                if not _is_stdlib(module):
                    findings.append(_finding(path, node, f"module level import of {module}"))
    return findings


def lazy_import_findings(core_dir: Path) -> list[str]:
    findings: list[str] = []
    for path in _python_files(core_dir):
        tree = _parse(path)
        module_level = {id(node) for node in _walk_outside_functions(tree)}
        for node in ast.walk(tree):
            if id(node) in module_level:
                continue
            for module in _imported_modules(node):
                if not _is_stdlib(module) and not _is_public_hermes(module):
                    findings.append(_finding(path, node, f"lazy import of {module}"))
    return findings


def async_def_findings(core_dir: Path) -> list[str]:
    return [
        _finding(path, node, f"async def {node.name}")
        for path in _python_files(core_dir)
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.AsyncFunctionDef)
    ]


def dashboard_import_findings(dashboard_dir: Path) -> list[str]:
    """Module-level imports of the path-loaded dashboard: stdlib, fastapi or pydantic, never relative."""
    findings: list[str] = []
    for path in _python_files(dashboard_dir):
        for node in _walk_outside_functions(_parse(path)):
            if isinstance(node, ast.ImportFrom) and node.level > 0:
                findings.append(_finding(path, node, "relative import"))
            for module in _imported_modules(node):
                if not _is_stdlib(module) and module.split(".")[0] not in DASHBOARD_THIRD_PARTY:
                    findings.append(_finding(path, node, f"module level import of {module}"))
    return findings


def module_length_findings(core_dir: Path, limit: int = MAX_MODULE_LINES) -> list[str]:
    findings: list[str] = []
    for path in _python_files(core_dir):
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > limit:
            findings.append(f"{path.name}: {lines} lines, limit {limit}")
    return findings


def _imports_connect_from_sqlite3(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == "sqlite3":
            names.update(
                alias.asname or alias.name for alias in node.names if alias.name == "connect"
            )
    return names


def raw_sqlite_connect_findings(core_dir: Path) -> list[str]:
    findings: list[str] = []
    for path in _python_files(core_dir):
        if path.name == "paths.py":
            continue
        tree = _parse(path)
        bare_names = _imports_connect_from_sqlite3(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_dotted = (
                isinstance(func, ast.Attribute)
                and func.attr == "connect"
                and isinstance(func.value, ast.Name)
                and func.value.id == "sqlite3"
            )
            is_bare = isinstance(func, ast.Name) and func.id in bare_names
            if is_dotted or is_bare:
                findings.append(_finding(path, node, "sqlite3.connect outside paths.py"))
    return findings


def _is_read_only_true(call: ast.Call) -> bool:
    return any(
        keyword.arg == "read_only"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in call.keywords
    )


def session_db_findings(core_dir: Path) -> list[str]:
    findings: list[str] = []
    for path in _python_files(core_dir):
        for node in ast.walk(_parse(path)):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            names_session_db = (isinstance(func, ast.Name) and func.id == "SessionDB") or (
                isinstance(func, ast.Attribute) and func.attr == "SessionDB"
            )
            if names_session_db and not _is_read_only_true(node):
                findings.append(_finding(path, node, "SessionDB built without read_only=True"))
    return findings


def _is_arguments_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id in ARGUMENT_NAMES


def _is_session_id_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value == "session_id"


def _sanctioned_node_ids(path: Path, tree: ast.AST) -> set[int]:
    """Return the ids of every node inside a sanctioned top-level function of this file."""
    skipped: set[int] = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef) and (path.name, node.name) in SANCTIONED_ARG_READS:
            skipped.update(id(inner) for inner in ast.walk(node))
    return skipped


def session_id_arg_findings(core_dir: Path) -> list[str]:
    """Report a read of `session_id` from the tool arguments (TOOL-06).

    Only the functions in `SANCTIONED_ARG_READS` may read it.
    """
    findings: list[str] = []
    for path in _python_files(core_dir):
        tree = _parse(path)
        skipped = _sanctioned_node_ids(path, tree)
        for node in ast.walk(tree):
            if id(node) in skipped:
                continue
            if (
                isinstance(node, ast.Subscript)
                and _is_arguments_name(node.value)
                and _is_session_id_literal(node.slice)
            ):
                findings.append(_finding(path, node, "session_id read from the tool arguments"))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in ARGUMENT_READERS
                and _is_arguments_name(node.func.value)
                and node.args
                and _is_session_id_literal(node.args[0])
            ):
                findings.append(_finding(path, node, "session_id read from the tool arguments"))
    return findings


def todo_mention_findings(plugin_dir: Path) -> list[str]:
    """Report a Python file, except tool_text.py, whose source text holds "todo" in any case."""
    findings: list[str] = []
    for path in _python_files(plugin_dir):
        if path.name == "tool_text.py" and path.parent.name == "session_tasks":
            continue
        if "todo" in path.read_text(encoding="utf-8").lower():
            findings.append(f"{path.relative_to(plugin_dir).as_posix()}: mentions todo")
    return findings


def _assigns_limit_literal(node: ast.AST) -> bool:
    """True for `SESSION_ID_MAX = 256` or `SESSION_ID_MAX: int = 256`, never for a read."""
    if isinstance(node, ast.Assign):
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        value = node.value
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        names = [node.target.id]
        value = node.value
    else:
        return False
    return SESSION_ID_LIMIT_NAME in names and isinstance(value, ast.Constant)


def session_id_max_findings(plugin_dir: Path) -> list[str]:
    """Report each file with a module-level literal assignment of the session id limit (D-56)."""
    return [
        path.relative_to(plugin_dir).as_posix()
        for path in _python_files(plugin_dir)
        if any(_assigns_limit_literal(node) for node in _parse(path).body)
    ]


def _write_module(directory: Path, source: str, name: str = "bad.py") -> None:
    (directory / name).write_text(source, encoding="utf-8")


# ---- guards over the real tree ----


def test_plugin_dir_holds_no_dependency_manifest() -> None:
    assert manifest_findings(PLUGIN_DIR) == []


def test_core_module_level_imports_are_stdlib_or_relative() -> None:
    assert module_level_import_findings(CORE_DIR) == []


def test_core_lazy_imports_use_the_public_hermes_allowlist() -> None:
    assert lazy_import_findings(CORE_DIR) == []


def test_core_defines_no_async_def() -> None:
    assert async_def_findings(CORE_DIR) == []


def test_dashboard_defines_no_async_def() -> None:
    assert async_def_findings(PLUGIN_DIR / "dashboard") == []


def test_dashboard_module_level_imports_are_stdlib_fastapi_or_pydantic() -> None:
    assert dashboard_import_findings(PLUGIN_DIR / "dashboard") == []


def test_core_modules_stay_under_500_lines() -> None:
    assert module_length_findings(CORE_DIR) == []


def test_raw_sqlite_connect_lives_only_in_paths() -> None:
    assert raw_sqlite_connect_findings(CORE_DIR) == []


def test_session_db_is_always_built_read_only() -> None:
    assert session_db_findings(CORE_DIR) == []


def test_core_never_reads_session_id_from_the_tool_arguments() -> None:
    assert session_id_arg_findings(CORE_DIR) == []


def test_plugin_python_files_never_mention_todo_outside_tool_text() -> None:
    assert todo_mention_findings(PLUGIN_DIR) == []


def test_session_id_max_has_one_literal_home() -> None:
    assert session_id_max_findings(PLUGIN_DIR) == [SESSION_ID_LIMIT_HOME]


# ---- self-tests: each guard reports a bad module ----


def test_manifest_guard_reports_a_pyproject_in_the_plugin_dir(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "pkg" / "ok.py").write_text("x = 1\n", encoding="utf-8")

    assert manifest_findings(tmp_path) == ["pkg/pyproject.toml"]


def test_module_level_import_guard_reports_a_third_party_import(tmp_path: Path) -> None:
    _write_module(tmp_path, "import json\nfrom . import sibling\nimport requests\n")

    findings = module_level_import_findings(tmp_path)

    assert len(findings) == 1
    assert "requests" in findings[0]


def test_lazy_import_guard_reports_a_private_hermes_module(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "def f():\n"
        "    from plugins.plugin_storage import plugin_db\n"
        "    import hermes_cli.sqlite_util\n"
        "    return plugin_db, hermes_cli\n",
    )

    findings = lazy_import_findings(tmp_path)

    assert len(findings) == 1
    assert "hermes_cli.sqlite_util" in findings[0]


def test_async_def_guard_reports_an_async_function(tmp_path: Path) -> None:
    _write_module(tmp_path, "def ok():\n    pass\n\nasync def bad():\n    pass\n")

    findings = async_def_findings(tmp_path)

    assert len(findings) == 1
    assert "bad" in findings[0]


def test_dashboard_import_guard_reports_relative_and_third_party_imports(
    tmp_path: Path,
) -> None:
    _write_module(
        tmp_path,
        "import json\n"
        "from fastapi import APIRouter\n"
        "from pydantic import BaseModel\n"
        "from . import x\n"
        "import requests\n"
        "\n"
        "def f():\n"
        "    import numpy\n"
        "    from . import y\n"
        "    return numpy, y\n",
    )

    findings = dashboard_import_findings(tmp_path)

    assert len(findings) == 2
    assert any("relative import" in f for f in findings)
    assert any("requests" in f for f in findings)


def test_module_length_guard_reports_a_501_line_module_and_not_a_500_line_one(
    tmp_path: Path,
) -> None:
    _write_module(tmp_path, "x = 1\n" * 501, "long.py")
    _write_module(tmp_path, "x = 1\n" * 500, "edge.py")

    findings = module_length_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].startswith("long.py")


def test_raw_connect_guard_reports_sqlite3_connect_outside_paths(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "import sqlite3\nfrom sqlite3 import connect as c\na = sqlite3.connect('x')\nb = c('y')\n",
    )
    _write_module(tmp_path, "import sqlite3\na = sqlite3.connect('x')\n", "paths.py")

    findings = raw_sqlite_connect_findings(tmp_path)

    assert len(findings) == 2
    assert all(finding.startswith("bad.py") for finding in findings)


def test_session_db_guard_reports_a_writable_session_db(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "def f(SessionDB, mod):\n"
        "    a = SessionDB()\n"
        "    b = SessionDB(read_only=False)\n"
        "    c = mod.SessionDB(read_only=True)\n"
        "    return a, b, c\n",
    )

    findings = session_db_findings(tmp_path)

    assert len(findings) == 2


def test_session_id_guard_reports_subscript_get_and_pop_on_the_arguments(tmp_path: Path) -> None:
    _write_module(
        tmp_path,
        "def f(args, function_args, other):\n"
        "    a = args['session_id']\n"
        "    b = function_args.get('session_id', '')\n"
        "    c = args.pop('session_id', None)\n"
        "    d = other['session_id']\n"
        "    e = args.get('text')\n"
        "    return a, b, c, d, e\n",
    )

    assert len(session_id_arg_findings(tmp_path)) == 3


def test_session_id_guard_allows_only_the_sanctioned_function(tmp_path: Path) -> None:
    read = "    return args.get('session_id')\n"
    _write_module(
        tmp_path,
        f"def read_target(args):\n{read}\ndef other(args):\n{read}",
        "copy_args.py",
    )
    assert len(session_id_arg_findings(tmp_path)) == 1

    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    _write_module(other_dir, f"def read_target(args):\n{read}", "board_tools.py")
    assert len(session_id_arg_findings(other_dir)) == 1


def test_todo_guard_reports_any_letter_case_and_skips_tool_text(tmp_path: Path) -> None:
    (tmp_path / "session_tasks").mkdir()
    _write_module(tmp_path / "session_tasks", "x = 'ToDo'\n", "tool_text.py")
    _write_module(tmp_path / "session_tasks", "y = 'TODO list'\n", "other.py")
    _write_module(tmp_path, "z = 1\n", "clean.py")

    assert todo_mention_findings(tmp_path) == ["session_tasks/other.py: mentions todo"]


def test_session_id_max_guard_reports_each_literal_and_skips_reads(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.py").write_text("SESSION_ID_MAX = 256\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("SESSION_ID_MAX: int = 128\n", encoding="utf-8")
    (tmp_path / "read.py").write_text("SESSION_ID_MAX: int = core().LIMIT\n", encoding="utf-8")
    (tmp_path / "other.py").write_text("MAX_COPY_IDS = 100\n", encoding="utf-8")

    assert session_id_max_findings(tmp_path) == ["a/one.py", "two.py"]


# ---- home guard helpers ----


def test_home_guard_reports_a_new_file_under_the_plugin_dir(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin-data" / "hermes-session-tasks"
    plugin_dir.mkdir(parents=True)
    before = snapshot(tmp_path)

    (plugin_dir / "data.db").write_text("x", encoding="utf-8")

    assert new_entries(before, snapshot(tmp_path)) == ("plugin-data/hermes-session-tasks/data.db",)


def test_home_guard_reports_a_new_plugin_dir_and_snapshots_a_missing_one_as_none(
    tmp_path: Path,
) -> None:
    before = snapshot(tmp_path)
    (tmp_path / "plugin-data" / "hermes-session-tasks").mkdir(parents=True)

    assert before is None
    assert new_entries(before, snapshot(tmp_path)) == ("plugin-data/hermes-session-tasks",)


def test_home_guard_reports_a_rewrite_of_an_existing_file(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin-data" / "hermes-session-tasks"
    plugin_dir.mkdir(parents=True)
    db_file = plugin_dir / "data.db"
    db_file.write_text("x", encoding="utf-8")
    before = snapshot(tmp_path)

    db_file.write_text("longer", encoding="utf-8")

    assert new_entries(before, snapshot(tmp_path)) == ("plugin-data/hermes-session-tasks/data.db",)


def test_home_guard_reports_a_same_size_rewrite_by_its_changed_time(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin-data" / "hermes-session-tasks"
    plugin_dir.mkdir(parents=True)
    db_file = plugin_dir / "data.db"
    db_file.write_text("x", encoding="utf-8")
    os.utime(db_file, ns=(1_000_000_000, 1_000_000_000))
    before = snapshot(tmp_path)

    db_file.write_text("y", encoding="utf-8")
    os.utime(db_file, ns=(2_000_000_000, 2_000_000_000))

    assert new_entries(before, snapshot(tmp_path)) == ("plugin-data/hermes-session-tasks/data.db",)


def test_home_guard_ignores_sqlite_sidecars_and_other_paths(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugin-data" / "hermes-session-tasks"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "data.db").write_text("x", encoding="utf-8")
    before = snapshot(tmp_path)

    for name in ("data.db-wal", "data.db-shm", "data.db-journal"):
        (plugin_dir / name).write_text("x", encoding="utf-8")
    (tmp_path / "state.db-wal").write_text("x", encoding="utf-8")
    (tmp_path / "gateway.lock").write_text("x", encoding="utf-8")
    (tmp_path / "plugin-data" / "other-plugin").mkdir()

    assert new_entries(before, snapshot(tmp_path)) == ()


# ---- session guard: the run itself fails ----

INNER_WRITES_PLUGIN_DIR = """
from pathlib import Path


def test_inner_writes_the_plugin_dir():
    target = Path.home() / ".hermes" / "plugin-data" / "hermes-session-tasks"
    target.mkdir(parents=True, exist_ok=True)
    (target / "data.db").write_text("x", encoding="utf-8")
"""

INNER_REWRITES_DATA_FILE = """
from pathlib import Path


def test_inner_rewrites_the_data_file():
    target = Path.home() / ".hermes" / "plugin-data" / "hermes-session-tasks" / "data.db"
    target.write_text("a longer body", encoding="utf-8")
"""

INNER_WRITES_NOTHING = """
def test_inner_writes_nothing():
    assert True
"""


def _run_inner_session(
    pytester: pytest.Pytester,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    existing_db: bool = False,
) -> tuple[pytest.RunResult, str]:
    home = pytester.path / "home"
    (home / ".hermes" / "plugin-data").mkdir(parents=True)
    if existing_db:
        plugin_dir = home / ".hermes" / "plugin-data" / "hermes-session-tasks"
        plugin_dir.mkdir()
        (plugin_dir / "data.db").write_text("x", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setenv("PYTHONPATH", str(TESTS_DIR))
    pytester.makepyfile(test_inner=source)
    result = pytester.runpytest_subprocess("-p", "home_guard", "-p", "no:cacheprovider")
    return result, result.stdout.str() + result.stderr.str()


def test_session_guard_fails_a_passing_run_that_writes_the_real_plugin_dir(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, output = _run_inner_session(pytester, monkeypatch, INNER_WRITES_PLUGIN_DIR)

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    assert "1 passed" in output
    assert (
        "real Hermes home changed: plugin-data/hermes-session-tasks, "
        "plugin-data/hermes-session-tasks/data.db"
    ) in output


def test_session_guard_fails_a_run_that_rewrites_an_existing_real_data_file(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, output = _run_inner_session(
        pytester, monkeypatch, INNER_REWRITES_DATA_FILE, existing_db=True
    )

    assert result.ret == pytest.ExitCode.TESTS_FAILED
    assert "1 passed" in output
    assert "real Hermes home changed: plugin-data/hermes-session-tasks/data.db" in output


def test_session_guard_passes_a_run_that_leaves_the_real_plugin_dir_alone(
    pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, output = _run_inner_session(pytester, monkeypatch, INNER_WRITES_NOTHING)

    assert result.ret == pytest.ExitCode.OK
    assert "real Hermes home changed" not in output
