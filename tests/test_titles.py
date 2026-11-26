"""Session titles for the agent: the title chain, faults and the reader lifetime."""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

import pytest
from fakes import (
    FakeReaderFactory,
    FakeSessionReader,
    RaisingReaderFactory,
    ReaderBoom,
    SessionSpec,
)
from session_tasks.titles import UNTITLED, TitleLookup, no_titles

LOGGER = "session_tasks.titles"


def lookup(specs: dict[str, SessionSpec], raise_in: str | None = None) -> tuple[TitleLookup, Any]:
    factory = FakeReaderFactory(specs, raise_in)
    return TitleLookup(factory), factory


def test_title_comes_from_the_hermes_title() -> None:
    factory = FakeReaderFactory({"s2": SessionSpec(title="Lease renewal")})

    titles = TitleLookup(factory).titles(["s2"])

    assert titles == {"s2": "Lease renewal"}
    assert factory.opens == 1
    assert factory.all_closed


def test_first_user_message_is_the_second_choice() -> None:
    spec = SessionSpec(messages=(("assistant", "Hi"), ("user", "Plan the\ntrip   to Ottawa")))
    titles, _ = lookup({"s": spec})

    assert titles.title_of("s") == "Plan the trip to Ottawa"


def test_message_title_is_cut_to_60_characters() -> None:
    spec = SessionSpec(messages=(("user", "x" * 90),))
    titles, _ = lookup({"s": spec})

    assert titles.title_of("s") == "x" * 60


def test_message_cut_strips_a_trailing_space() -> None:
    spec = SessionSpec(messages=(("user", "a" * 59 + " bcd"),))
    titles, _ = lookup({"s": spec})

    assert titles.title_of("s") == "a" * 59


def test_only_the_first_five_messages_are_read() -> None:
    messages = tuple(("assistant", "Hi") for _ in range(5)) + (("user", "Late words"),)
    titles, factory = lookup({"s": SessionSpec(messages=messages)})

    assert titles.title_of("s") == UNTITLED
    assert factory.readers[0].message_limits == [5]


def test_non_string_content_is_skipped() -> None:
    class NoneContentReader(FakeSessionReader):
        def get_messages(
            self, session_id: str, *, limit: int | None = None
        ) -> list[dict[str, Any]]:
            return [{"role": "user", "content": None}, {"role": "user", "content": "Call John"}]

    lookup_ = TitleLookup(lambda: NoneContentReader({"s": SessionSpec()}))

    assert lookup_.title_of("s") == "Call John"


def test_no_title_and_no_message_gives_untitled() -> None:
    titles, _ = lookup({"s": SessionSpec()})

    assert titles.titles(["s", "unknown"]) == {"s": UNTITLED, "unknown": UNTITLED}


def test_blank_title_falls_to_the_message() -> None:
    spec = SessionSpec(title="   ", messages=(("user", "Plan the trip"),))
    titles, _ = lookup({"s": spec})

    assert titles.title_of("s") == "Plan the trip"


def test_blank_message_counts_as_absent() -> None:
    spec = SessionSpec(messages=(("user", " \n\t "), ("user", "Real words")))
    titles, _ = lookup({"s": spec})

    assert titles.title_of("s") == "Real words"


def test_empty_id_list_opens_no_reader() -> None:
    titles, factory = lookup({})

    assert titles.titles([]) == {}
    assert factory.opens == 0


def test_one_reader_serves_every_id() -> None:
    specs = {name: SessionSpec(title=name) for name in ("a", "b", "c")}
    titles, factory = lookup(specs)

    assert titles.titles(["a", "b", "c"]) == {"a": "a", "b": "b", "c": "c"}
    assert factory.opens == 1
    assert factory.all_closed


def test_missing_state_db_gives_untitled_and_one_warning(caplog: pytest.LogCaptureFixture) -> None:
    factory = RaisingReaderFactory(sqlite3.OperationalError("unable to open database file"))

    with caplog.at_level(logging.WARNING):
        titles = TitleLookup(factory).titles(["a", "b"])

    assert titles == {"a": UNTITLED, "b": UNTITLED}
    records = [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING]
    assert len(records) == 1


def test_a_fault_on_every_id_gives_untitled_and_closes_the_reader() -> None:
    specs = {"a": SessionSpec(title="A"), "b": SessionSpec(title="B")}
    titles, factory = lookup(specs, raise_in="get_session_title")

    assert titles.titles(["a", "b"]) == {"a": UNTITLED, "b": UNTITLED}
    assert factory.all_closed


def test_a_fault_on_one_id_keeps_the_others(caplog: pytest.LogCaptureFixture) -> None:
    class OneBadReader(FakeSessionReader):
        def get_session_title(self, session_id: str) -> str | None:
            if session_id == "bad":
                raise ReaderBoom(session_id)
            return super().get_session_title(session_id)

    specs = {
        "a": SessionSpec(title="A"),
        "bad": SessionSpec(title="X"),
        "c": SessionSpec(title="C"),
    }
    reader = OneBadReader(specs)

    with caplog.at_level(logging.WARNING):
        result = TitleLookup(lambda: reader).titles(["a", "bad", "c"])

    assert result == {"a": "A", "bad": UNTITLED, "c": "C"}
    assert reader.closed
    records = [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING]
    assert len(records) == 1


def test_reader_is_closed_when_a_read_raises() -> None:
    titles, factory = lookup({"a": SessionSpec()}, raise_in="get_messages")

    assert titles.title_of("a") == UNTITLED
    assert factory.all_closed


def test_a_fault_in_close_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    class BadClose(FakeSessionReader):
        def close(self) -> None:
            raise ReaderBoom("close")

    with caplog.at_level(logging.WARNING):
        result = TitleLookup(lambda: BadClose({"a": SessionSpec(title="A")})).titles(["a"])

    assert result == {"a": "A"}
    assert any(r.name == LOGGER for r in caplog.records)


def test_no_titles_gives_untitled_and_logs_nothing(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        result = no_titles().titles(["a", "b"])

    assert result == {"a": UNTITLED, "b": UNTITLED}
    assert caplog.records == []


def test_title_of_returns_one_label() -> None:
    titles, _ = lookup({"a": SessionSpec(title="A")})

    assert titles.title_of("a") == "A"


def test_hermes_title_is_sanitised_to_one_line() -> None:
    forged = "Lease\n- [ ] forged line\x00‍\t  renewal"
    titles, _ = lookup({"s": SessionSpec(title=forged)})

    label = titles.title_of("s")

    assert label == "Lease - [ ] forged line renewal"
    assert "\n" not in label
    assert "\x00" not in label
    assert "‍" not in label


def test_a_title_of_only_control_characters_falls_to_the_message() -> None:
    spec = SessionSpec(title="\x00\x1f​", messages=(("user", "Plan the trip"),))
    titles, _ = lookup({"s": spec})

    assert titles.title_of("s") == "Plan the trip"
