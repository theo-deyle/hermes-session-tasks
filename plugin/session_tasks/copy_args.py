"""Arguments of the cross-session tools: board_copy, and the session_id of board_read that names another board.

One parser serves the tool and the route. No I/O. The calling session never comes from here (TOOL-06).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from . import edit_args
from .model import BoardError

SESSION_ID_MAX = 256
MAX_COPY_IDS = 100
MAX_RAW_IDS = 1000

FROM_REQUIRED = "from_session_id is required: a session id from board_sessions"
ITEM_IDS_BAD = "item_ids must be a list of item ids"
ITEM_IDS_EMPTY = "item_ids must name at least one item; leave it out to copy every open item"
TARGET_BAD = "session_id must be a session id from board_sessions"
SESSION_ID_LONG = f"a session id has at most {SESSION_ID_MAX} characters"
TOO_MANY_IDS = f"at most {MAX_COPY_IDS} item ids per call"


class CopyArgsError(BoardError):
    """The arguments of a `board_copy` call, or the target of `board_read`, are not valid."""


@dataclass(frozen=True, slots=True)
class CopyArgs:
    from_session_id: str
    item_ids: tuple[int, ...] | None
    base_rev: int | None


def _session_id(value: object, missing: str) -> str:
    """Return a stripped session id of 1 to `SESSION_ID_MAX` characters."""
    if not isinstance(value, str) or not value.strip():
        raise CopyArgsError(missing)
    text = value.strip()
    if len(text) > SESSION_ID_MAX:
        raise CopyArgsError(SESSION_ID_LONG)
    return text


def _raw_ids(value: object) -> Sequence[object]:
    """Return the raw id list from a list, a JSON string of a list, or one whole number."""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                value = json.loads(text)
            except ValueError:
                raise CopyArgsError(ITEM_IDS_BAD) from None
        elif edit_args.whole_number(text) is None:
            raise CopyArgsError(ITEM_IDS_BAD)
        else:
            value = [text]
    elif isinstance(value, int) and not isinstance(value, bool):
        value = [value]
    if not isinstance(value, list):
        raise CopyArgsError(ITEM_IDS_BAD)
    return value


def _item_ids(value: object) -> tuple[int, ...] | None:
    if value is None:
        return None
    raw = _raw_ids(value)
    if not raw:
        raise CopyArgsError(ITEM_IDS_EMPTY)
    if len(raw) > MAX_RAW_IDS:
        raise CopyArgsError(TOO_MANY_IDS)
    ids: dict[int, None] = {}
    for index, entry in enumerate(raw):
        number = edit_args.whole_number(entry)
        if not number:
            raise CopyArgsError(f"item_ids[{index}] must be a whole number of 1 or more")
        ids[number] = None
    if len(ids) > MAX_COPY_IDS:
        raise CopyArgsError(TOO_MANY_IDS)
    return tuple(ids)


def parse(args: Mapping[str, object]) -> CopyArgs:
    """Parse `from_session_id`, `item_ids` and `base_rev`; other keys are ignored.

    Raise `CopyArgsError` for any argument that is not valid.
    """
    try:
        base_rev = edit_args.base_rev_arg(args.get("base_rev"))
    except edit_args.EditArgsError as error:
        raise CopyArgsError(str(error)) from None
    return CopyArgs(
        _session_id(args.get("from_session_id"), FROM_REQUIRED),
        _item_ids(args.get("item_ids")),
        base_rev,
    )


def read_target(args: Mapping[str, object]) -> str | None:
    """Return the board `board_read` should read, or None for the caller's own board.

    This is the one sanctioned read of `session_id` from the tool arguments. It only
    names a board to read. The calling session comes from the Hermes keyword (TOOL-06).
    """
    value = args.get("session_id")
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _session_id(value, TARGET_BAD)
