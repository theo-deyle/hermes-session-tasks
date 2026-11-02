"""Session titles for the agent: the title chain, faults and the reader lifetime."""

from __future__ import annotations

from fakes import FakeReaderFactory, SessionSpec
from session_tasks.titles import TitleLookup


def test_title_comes_from_the_hermes_title() -> None:
    factory = FakeReaderFactory({"s2": SessionSpec(title="Lease renewal")})

    titles = TitleLookup(factory).titles(["s2"])

    assert titles == {"s2": "Lease renewal"}
    assert factory.opens == 1
    assert factory.all_closed
