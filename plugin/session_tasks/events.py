"""Publish `board.updated` after a committed write. The only caller of `broadcast_plugin_event`.

The writers call a listener after the commit, once per changed write. A publish fault never
fails a write: `publish` logs one warning and returns. The Hermes import stays inside
`publish`, so this module loads without Hermes. Events reach only the Desktop clients of the
process that makes the write; the pane polls as well, and nothing here relays between processes.
The payload holds ids, a revision and the actor. It never holds board text.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeAlias

from . import paths
from .model import Actor

log = logging.getLogger(__name__)

PLUGIN_ID = paths.PLUGIN_NAME
EVENT = "board.updated"

# (root_id, session_id, rev, actor)
Publisher: TypeAlias = Callable[[str, str, int, Actor], None]
# (root_id, session_id, rev)
WriteListener: TypeAlias = Callable[[str, str, int], None]


def publish(root_id: str, session_id: str, rev: int, actor: Actor) -> None:
    """Broadcast `board.updated` to the Desktop clients. Log a warning on any fault."""
    payload = {"session_id": session_id, "root_id": root_id, "rev": rev, "actor": actor}
    try:
        from hermes_cli.plugin_events import (  # pyright: ignore[reportMissingImports]
            broadcast_plugin_event,
        )

        broadcast_plugin_event(PLUGIN_ID, EVENT, payload)
    except Exception:
        log.warning("board.updated publish failed", exc_info=True)


def listener(actor: Actor, publisher: Publisher = publish) -> WriteListener:
    """Bind an actor, so the tool writer and the route writer share one listener type."""

    def after_write(root_id: str, session_id: str, rev: int) -> None:
        publisher(root_id, session_id, rev, actor)

    return after_write
