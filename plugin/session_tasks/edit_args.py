"""Parse `board_edit` arguments into ops. One parser serves the hook and the handler.

The `pre_tool_call` hook sees the raw model arguments. The handler sees the arguments
after Hermes coerces them. This parser accepts both forms and returns equal values for
both. It does no I/O. Text is not cleaned or measured here: the store does that.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from .model import AddItem, BoardError, Op, RemoveItem, SetChecked, SetText
from .revision import check_base_rev, target_id

MAX_OPS = 100
OP_FIELDS: Mapping[str, frozenset[str]] = MappingProxyType({
    "add": frozenset({"op", "text", "checked", "parent_id", "parent_ref"}),
    "set_text": frozenset({"op", "item_id", "text"}),
    "set_checked": frozenset({"op", "item_id", "checked"}),
    "remove": frozenset({"op", "item_id"}),
})

MAX_WHOLE = 2**63 - 1
MAX_WHOLE_DIGITS = len(str(MAX_WHOLE))

OPS_NOT_LIST = "ops must be a JSON list of operations"
BASE_REV_BAD = "base_rev must be a whole number of 0 or more"
BASE_REV_MISSING = (
    "base_rev is required when an op targets an existing item. Call board_read first."
)


class EditArgsError(BoardError):
    """The arguments of a `board_edit` call are not a valid list of operations."""


@dataclass(frozen=True, slots=True)
class ParsedEdit:
    ops: tuple[Op, ...]
    base_rev: int | None
    confirmed: bool


def whole_number(value: object) -> int | None:
    """Return a whole number from 0 to `MAX_WHOLE` from an int (not a bool) or ASCII digits.

    A value outside the SQLite integer range gives None, so it never reaches the store.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        digits = value.strip()
        if not (digits.isascii() and digits.isdigit()):
            return None
        if len(digits.lstrip("0")) > MAX_WHOLE_DIGITS:
            return None
        value = int(digits)
    if isinstance(value, int) and 0 <= value <= MAX_WHOLE:
        return value
    return None


def _id(value: object, field: str, minimum: int) -> int:
    number = whole_number(value)
    if number is None:
        raise EditArgsError(f"{field} must be a whole number")
    if number < minimum:
        raise EditArgsError(f"{field} must be {minimum} or more")
    return number


def _flag(value: object, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"
    raise EditArgsError(f"{field} must be true or false")


def _required(item: Mapping[str, object], kind: str, field: str) -> object:
    value = item.get(field)
    if value is None:
        raise EditArgsError(f"{kind} needs {field}")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise EditArgsError("text must be a string")
    return value


def _optional_id(item: Mapping[str, object], field: str, minimum: int) -> int | None:
    value = item.get(field)
    return None if value is None else _id(value, field, minimum)


def _build_add(item: Mapping[str, object]) -> Op:
    checked = item.get("checked")
    return AddItem(
        text=_text(_required(item, "add", "text")),
        checked=False if checked is None else _flag(checked, "checked"),
        parent_id=_optional_id(item, "parent_id", 1),
        parent_ref=_optional_id(item, "parent_ref", 0),
    )


def _build_set_text(item: Mapping[str, object]) -> Op:
    item_id = _id(_required(item, "set_text", "item_id"), "item_id", 1)
    return SetText(item_id, _text(_required(item, "set_text", "text")))


def _build_set_checked(item: Mapping[str, object]) -> Op:
    item_id = _id(_required(item, "set_checked", "item_id"), "item_id", 1)
    return SetChecked(item_id, _flag(_required(item, "set_checked", "checked"), "checked"))


def _build_remove(item: Mapping[str, object]) -> Op:
    return RemoveItem(_id(_required(item, "remove", "item_id"), "item_id", 1))


_BUILDERS = {
    "add": _build_add,
    "set_text": _build_set_text,
    "set_checked": _build_set_checked,
    "remove": _build_remove,
}


def _as_object(raw: object) -> Mapping[str, object]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raise EditArgsError("an operation must be an object") from None
    if not isinstance(raw, dict):
        raise EditArgsError("an operation must be an object")
    return raw


def _build_op(raw: object) -> Op:
    item = _as_object(raw)
    kind = item.get("op")
    if not isinstance(kind, str) or kind not in OP_FIELDS:
        raise EditArgsError("op must be one of add, set_text, set_checked, remove")
    unknown = sorted(str(key) for key in item if key not in OP_FIELDS[kind])
    if unknown:
        raise EditArgsError(f"unknown field {unknown[0]!r} for {kind}")
    return _BUILDERS[kind](item)


def _parse_op(raw: object, index: int) -> Op:
    try:
        return _build_op(raw)
    except EditArgsError as exc:
        raise EditArgsError(str(exc), index) from None


def _op_list(value: object) -> Sequence[object]:
    if value is None:
        raise EditArgsError("ops is required: a list of operations")
    decoded: object = value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            raise EditArgsError(OPS_NOT_LIST) from None
    if isinstance(decoded, dict):
        decoded = [decoded]
    if not isinstance(decoded, list):
        raise EditArgsError(OPS_NOT_LIST)
    if len(decoded) > MAX_OPS:
        raise EditArgsError(f"at most {MAX_OPS} operations per call")
    return decoded


def base_rev_arg(value: object) -> int | None:
    if value is None:
        return None
    number = whole_number(value)
    if number is None:
        raise EditArgsError(BASE_REV_BAD)
    try:
        return check_base_rev(number)
    except ValueError:
        raise EditArgsError(BASE_REV_BAD) from None


def _confirmed(value: object) -> bool:
    return False if value is None else _flag(value, "confirmed")


def parse(args: Mapping[str, object]) -> ParsedEdit:
    """Return the ops, base_rev and confirmed flag of a `board_edit` call.

    Raise `EditArgsError` for any argument that is not valid. An error about one op
    carries that op's index. Keys outside `ops`, `base_rev` and `confirmed` are ignored.
    """
    items = _op_list(args.get("ops"))
    ops = tuple(_parse_op(raw, index) for index, raw in enumerate(items))
    base_rev = base_rev_arg(args.get("base_rev"))
    if base_rev is None:
        for index, op in enumerate(ops):
            if target_id(op) is not None:
                raise EditArgsError(BASE_REV_MISSING, index)
    return ParsedEdit(ops=ops, base_rev=base_rev, confirmed=_confirmed(args.get("confirmed")))
