"""Script run by the gateway venv Python against a temporary HERMES_HOME. It prints one JSON line.

Arguments: plugin dir, Hermes checkout dir. The script runs 30 scripted turns on two boards
through Hermes's own hook dispatch (`invoke_hook`) and Hermes's own message composer
(`compose_user_api_content`). The "edits" board gets edits from Theo, the "quiet" board does
not. Both boards get the same agent edits. This script is not a pytest module: the gateway
venv has no pytest. It never touches the real Hermes home, because the caller sets HERMES_HOME
to a temporary directory.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN_DIR, CHECKOUT_DIR = sys.argv[1:3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hermes_snippet_setup import link_and_enable, stub_gateway_server  # noqa: E402

# Link and enable, and stub the gateway module, before any Hermes import.
link_and_enable(Path(os.environ["HERMES_HOME"]), Path(PLUGIN_DIR))
sys.path.insert(0, CHECKOUT_DIR)
sys.path.insert(0, PLUGIN_DIR)
stub_gateway_server(lambda name, payload: None)

import hermes_cli.plugins as hermes_plugins  # noqa: E402  # pyright: ignore[reportMissingImports]
from agent.turn_context import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    compose_user_api_content,
)
from model_tools import handle_function_call  # noqa: E402  # pyright: ignore[reportMissingImports]
from session_tasks import paths  # noqa: E402
from session_tasks.model import AddItem, Op, RemoveItem, SetChecked, SetText  # noqa: E402
from session_tasks.store import BoardStore  # noqa: E402

TURNS = 30
EDITS = "edits"
QUIET = "quiet"
BULK = 60


def store() -> BoardStore:
    return BoardStore(paths.connect)


def rev_of(root: str) -> int:
    return store().get_board(root).rev


def id_of(root: str, text: str) -> int:
    for item in store().get_board(root).items:
        if item.text == text:
            return item.id
    raise LookupError(f"no item with text {text!r} on board {root!r}")


def agent_edit(root: str, ops: list[dict[str, object]]) -> None:
    args: dict[str, object] = {"ops": ops, "base_rev": rev_of(root)}
    reply = json.loads(handle_function_call("board_edit", args, session_id=root))
    if reply.get("ok") is not True:
        raise RuntimeError(f"agent edit failed on {root!r}: {reply}")


def theo(root: str, ops: list[Op]) -> None:
    store().apply(root, ops, actor="user", base_rev=rev_of(root))


def agent_turns(root: str, turn: int) -> None:
    if turn == 3:
        agent_edit(
            root, [{"op": "add", "text": "Plan step one"}, {"op": "add", "text": "Plan step two"}]
        )
    if turn == 8:
        agent_edit(
            root, [{"op": "set_checked", "item_id": id_of(root, "Plan step one"), "checked": True}]
        )


def theo_turns(root: str, turn: int) -> None:
    if turn == 5:
        theo(root, [AddItem("Call John"), AddItem("Book the van")])
    if turn == 12:
        theo(
            root,
            [
                SetChecked(id_of(root, "Call John"), True),
                SetText(id_of(root, "Book the van"), "Book the van for Friday"),
            ],
        )
    if turn == 20:
        theo(root, [RemoveItem(id_of(root, "Book the van for Friday"))])
    if turn == 25:
        theo(root, [AddItem(f"Bulk {n}") for n in range(1, BULK + 1)])
        theo(root, [RemoveItem(id_of(root, f"Bulk {n}")) for n in range(1, BULK + 1)])


def hook_text(root: str, turn: int) -> str | None:
    results = hermes_plugins.invoke_hook(
        "pre_llm_call",
        session_id=root,
        task_id="t1",
        turn_id=f"u{turn}",
        user_message=f"turn {turn}",
        conversation_history=[],
        is_first_turn=turn == 1,
        model="m",
        platform="cli",
        parent_session_id="",
        sender_id="",
    )
    parts = [item for item in results if isinstance(item, str) and item.strip()]
    return "\n\n".join(parts) if parts else None


def run_turn(root: str, turn: int) -> dict[str, object]:
    note = hook_text(root, turn)
    content = f"turn {turn}"
    composed = compose_user_api_content(content, "", note or "")
    added = 0 if composed is None else len(composed) - len(content)
    return {"turn": turn, "note": note, "added": added}


def main() -> None:
    hermes_plugins.discover_plugins()
    out: dict[str, object] = {EDITS: [], QUIET: []}
    for turn in range(1, TURNS + 1):
        for root in (EDITS, QUIET):
            agent_turns(root, turn)
        theo_turns(EDITS, turn)
        if turn == 25:
            out["pointer_turn_rev"] = rev_of(EDITS)
        for root in (EDITS, QUIET):
            row = run_turn(root, turn)
            list_for_root = out[root]
            assert isinstance(list_for_root, list)
            list_for_root.append(row)
    print(json.dumps(out))


main()
