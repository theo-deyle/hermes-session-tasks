"""Build a test Hermes home for the live checks. Run it with the gateway venv Python (PyYAML).

The test home takes an allowlist of keys from the real config.yaml. Every messaging platform and
every listener is off, memory is off, and only the model provider plugin runs, plus the board
plugin with --with-plugin. The model provider reads the Claude Code credential store outside
HERMES_HOME, so the test home needs no key. This tool never links, copies or reads `.env`,
`auth.json` or `mcp-tokens`, and it has no option that would. It parses the source config in
memory and prints key names only, never a config value.

usage: make_home.py --out DIR [--with-plugin] [--source CONFIG] [--plugins-dir DIR] [--repo-plugin DIR]
Prints one JSON line. Exit 0 on success, 2 when it refuses to build (nothing is written).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

KEPT_KEYS = (
    "_config_version",
    "model",
    "agent",
    "compression",
    "prompt_caching",
    "streaming",
    "tool_loop_guardrails",
    "delegation",
    "display",
    "terminal",
    "code_execution",
    "browser",
    "web",
    "skills",
    "known_builtin_toolsets",
    "known_plugin_toolsets",
    "platform_toolsets",
    "session_reset",
    "smart_model_routing",
)
SLUG = "hermes-session-tasks"
SECRET_NAME = re.compile(r"(key|token|secret|pass|auth|cred|bearer)", re.I)
LISTENER_PLATFORMS = ("webhook", "api_server", "msgraph_webhook")
LISTENER_NAME = re.compile(r"(^|_)(port|listen|bind)(_|$)", re.I)
DEFAULT_SOURCE = Path.home() / ".hermes" / "config.yaml"
DEFAULT_PLUGINS = Path.home() / ".hermes" / "plugins"
DEFAULT_REPO_PLUGIN = Path(__file__).resolve().parents[3] / "plugin"
REFUSED = 2


class Refused(Exception):
    """The build stops. The message names keys and paths, never a config value."""


def _walk(node: object, path: str) -> None:
    """Raise Refused for a secret-looking string or a non-zero listener setting under a key."""
    if isinstance(node, Mapping):
        for key, value in node.items():
            where = f"{path}.{key}" if path else str(key)
            if SECRET_NAME.search(str(key)) and isinstance(value, str):
                raise Refused(f"a kept key looks like a secret: {where}")
            if LISTENER_NAME.search(str(key)) and _is_listener_value(value):
                raise Refused(f"a kept key sets a port, listen or bind value: {where}")
            _walk(value, where)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, f"{path}[{index}]")


def _is_listener_value(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value != 0
    return isinstance(value, str) and bool(value)


def test_home_config(
    source: Mapping[str, object], provider: str, with_plugin: bool
) -> dict[str, object]:
    """Return the config to write. Pure: it reads no file."""
    config: dict[str, object] = {key: source[key] for key in KEPT_KEYS if key in source}
    platforms = source.get("platforms")
    names = [str(name) for name in platforms] if isinstance(platforms, Mapping) else []
    for name in LISTENER_PLATFORMS:
        if name not in names:
            names.append(name)
    config["platforms"] = {name: {"enabled": False} for name in names}
    config["proxy"] = {"enabled": False}
    config["updates"] = {"check": False}
    config["memory"] = {"memory_enabled": False, "user_profile_enabled": False}
    enabled = [provider, SLUG] if with_plugin else [provider]
    plugins = source.get("plugins")
    entries = plugins.get("entries") if isinstance(plugins, Mapping) else None
    kept_entries = (
        {name: entries[name] for name in enabled if name in entries}
        if isinstance(entries, Mapping)
        else {}
    )
    config["plugins"] = {
        "enabled": enabled,
        "disabled": [],
        "entries": kept_entries,
        "auto_update_check_hours": 0,
    }
    return config


def _provider(source: Mapping[str, object]) -> str:
    model = source.get("model")
    provider = model.get("provider") if isinstance(model, Mapping) else None
    if not isinstance(provider, str) or not provider:
        raise Refused("the source config has no model.provider")
    return provider


def _check_out(out: Path, source_home: Path) -> None:
    if out == source_home or source_home in out.parents:
        raise Refused("the out dir is the source home or lies inside it")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise Refused("the out dir exists and is not empty")


def _parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a test Hermes home for the live checks.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--with-plugin", action="store_true")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--plugins-dir", default=str(DEFAULT_PLUGINS))
    parser.add_argument("--repo-plugin", default=str(DEFAULT_REPO_PLUGIN))
    return parser.parse_args()


def _write(out: Path, config: dict[str, object], links: dict[str, Path]) -> None:
    import yaml  # pyright: ignore[reportMissingModuleSource]

    out.mkdir(parents=True, exist_ok=True)
    out.chmod(0o700)
    plugins = out / "plugins"
    plugins.mkdir()
    descriptor = os.open(out / "config.yaml", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(yaml.safe_dump(config, sort_keys=False))
    for name, target in links.items():
        (plugins / name).symlink_to(target, target_is_directory=True)


def _build(args: argparse.Namespace) -> dict[str, object]:
    import yaml  # pyright: ignore[reportMissingModuleSource]

    source_path = Path(args.source).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    _check_out(out, source_path.parent)
    loaded = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, Mapping):
        raise Refused("the source config is not a mapping")
    provider = _provider(loaded)
    config = test_home_config(loaded, provider, args.with_plugin)
    _walk({key: value for key, value in config.items() if key in KEPT_KEYS}, "")
    _walk(config["plugins"], "plugins")
    provider_dir = Path(args.plugins_dir).expanduser() / provider
    if not provider_dir.is_dir():
        raise Refused("the provider plugin dir is missing")
    links = {provider: provider_dir.resolve()}
    if args.with_plugin:
        repo_plugin = Path(args.repo_plugin).expanduser()
        if not repo_plugin.is_dir():
            raise Refused("the repo plugin dir is missing")
        links[SLUG] = repo_plugin.resolve()
    _write(out, config, links)
    platforms = config["platforms"]
    off = sorted(platforms) if isinstance(platforms, Mapping) else []
    return {
        "home": str(out),
        "enabled": list(links),
        "kept_keys": sorted(config),
        "listeners_off": [*off, "proxy", "updates.check", "plugins.auto_update_check_hours"],
    }


def main() -> int:
    args = _parse()
    try:
        summary = _build(args)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return REFUSED
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
