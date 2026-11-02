"""Arguments of the cross-session tools: board_copy, and the session_id of board_read that names another board.

One parser serves the tool and the route. No I/O. The calling session never comes from here (TOOL-06).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import edit_args
from .model import BoardError

SESSION_ID_MAX = 256
MAX_COPY_IDS = 100

FROM_REQUIRED = "from_session_id is required: a session id from board_sessions"
ITEM_IDS_BAD = "item_ids must be a list of item ids"
ITEM_IDS_EMPTY = "item_ids must name at least one item; leave it out to copy every open item"
TARGET_BAD = "session_id must be a session id from board_sessions"


class CopyArgsError(BoardError):
    """The arguments of a `board_copy` call, or the target of `board_read`, are not valid."""


@dataclass(frozen=True, slots=True)
class CopyArgs:
    from_session_id: str
    item_ids: tuple[int, ...] | None
    base_rev: int | None


def parse(args: Mapping[str, object]) -> CopyArgs:
    """Parse `from_session_id`, `item_ids` and `base_rev`; other keys are ignored."""
    raw = args.get("item_ids")
    ids: tuple[int, ...] | None = None
    if isinstance(raw, list):
        ids = tuple(dict.fromkeys(n for n in map(edit_args.whole_number, raw) if n))
    try:
        base_rev = edit_args.base_rev_arg(args.get("base_rev"))
    except edit_args.EditArgsError as error:
        raise CopyArgsError(str(error)) from None
    return CopyArgs(str(args.get("from_session_id", "")).strip(), ids, base_rev)


def read_target(args: Mapping[str, object]) -> str | None:
    """Return the board `board_read` should read, or None for the caller's own board.

    This is the one sanctioned read of `session_id` from the tool arguments. It only
    names a board to read. The calling session comes from the Hermes keyword (TOOL-06).
    """
    value = args.get("session_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
