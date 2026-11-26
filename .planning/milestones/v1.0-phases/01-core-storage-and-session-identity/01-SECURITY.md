---
phase: "01"
slug: "core-storage-and-session-identity"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-30"
---

# Phase 01 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Caller to store | A tool handler or a REST route passes a session id, item text and a base revision into the store | Session id, free text, integers |
| Store to plugin SQLite file | `plugin_db` opens `<HERMES_HOME>/plugin-data/hermes-session-tasks/data.db` | Board rows, journal rows |
| Resolver to Hermes `state.db` | `SessionDB(read_only=True)` reads session lineage | Session ids, parent ids, kinds. Read only |
| Test suite to developer home | Every test runs under a tmp `HERMES_HOME` and a network block | None. The real home must not change |
| Dev tooling to package index | `uv sync` installs the pinned dev group | Locked versions, pypi.org only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering | rows.py, aliases.py SQL | high | mitigate | Every value goes through a `?` parameter. The three f-strings in `aliases.py:11` and `rows.py:149,153` hold only the table name constants | closed |
| T-01-02 | Tampering | model.sanitize_text | medium | mitigate | `sanitize_text` in `model.py` drops control, format, surrogate and private-use characters and collapses whitespace | closed |
| T-01-03 | Elevation of Privilege | lineage.SessionResolver.resolve | high | mitigate | A blank or non-string session id raises `InvalidSession` in `lineage.py` | closed |
| T-01-04 | Tampering | tests/conftest.py, tests/home_guard.py | medium | mitigate | Autouse tmp `HERMES_HOME` fixture; `home_guard.py` fails the run if the real plugin-data dir gains entries | closed |
| T-01-05 | Tampering | schema.migrate | medium | mitigate | `SchemaTooNew` raised in `schema.py` for a newer `user_version`; no downgrade path | closed |
| T-01-06 | Tampering | layout guards over plugin/session_tasks | medium | mitigate | `tests/test_layout.py` AST guards: production opens the file only through `plugin_db` | closed |
| T-01-07 | Tampering | store.apply across processes | high | mitigate | `BEGIN IMMEDIATE` in `db.py`, one connection per operation, spawn-process race tests in `tests/test_race.py` | closed |
| T-01-08 | Tampering | store cascade remove | high | mitigate | `revision.is_stale` marks a parent delete stale when any subtask changed after `base_rev` | closed |
| T-01-09 | Denial of Service | items and changes tables | medium | mitigate | `MAX_ITEMS = 100`, `MAX_TEXT_CHARS = 500` in `model.py`; journal pruned to 100 rows per board | closed |
| T-01-10 | Tampering | revision.check_base_rev | low | mitigate | A bool, non-int or negative `base_rev` raises `ValueError` before any connection opens | closed |
| T-01-11 | Denial of Service | markdown.parse and plan_import | medium | mitigate | One pass, depth clamp to one subtask level, lines over 500 code points skipped, import stops at free capacity | closed |
| T-01-12 | Spoofing | render and parse of `#<digits>` text | medium | mitigate | `render` escapes text that starts with `#<digits>`; 500-board round trip test | closed |
| T-01-13 | Tampering | session_reader.open_session_reader | high | mitigate | Only `SessionDB(read_only=True)` in `session_reader.py`; contract test proves `state.db` bytes unchanged | closed |
| T-01-14 | Elevation of Privilege | lineage delegate path | medium | mitigate | A delegate resolves to the delegator root with kind `delegate`; Phase 1 writes no board and no copy for it | closed |
| T-01-15 | Denial of Service | recursive resolve | low | mitigate | Visited set and `MAX_LINEAGE_HOPS = 20` in `lineage.py` | closed |
| T-01-16 | Information Disclosure | fork_copy | medium | mitigate | A branch gets its own root after the copy; branch isolation test in `tests/test_fork.py` | closed |
| T-01-17 | Tampering | tests/test_hermes_contract.py | high | mitigate | Subprocess gets a tmp `HERMES_HOME` and `PYTEST_CURRENT_TEST`; digest check on `state.db` | closed |
| T-01-18 | Tampering | scripts/check.sh coverage gate | low | mitigate | `fail_under = 80` with branch coverage in `pyproject.toml` | closed |
| T-01-19 | Information Disclosure | plugin-data/hermes-session-tasks/data.db | low | accept | See R-01-01 | closed |
| T-01-20 | Tampering | parse text cleaning | medium | mitigate | Parsed text goes through `model.sanitize_text` | closed |
| T-01-21 | Elevation of Privilege | SessionResolver.record_compaction | high | mitigate | A blank session id raises `InvalidSession`; tested in `tests/test_lineage.py` | closed |
| T-01-SC | Tampering | dev dependencies | high | mitigate | `scripts/check_pins.py` runs first in every `check.sh` run; rejects any locked package not from pypi.org | closed |

*Status: open · closed · open - below high threshold (non-blocking)*
*Severity: critical > high > medium > low - only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-01-01 | T-01-19 | The board file lives under `~/.hermes`, which is mode 0700 on devpc (verified 2026-10-30). No other local user can read it. The board holds task text only, no credentials. | Phase 1 plan 01-06 threat model | 2026-10-30 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-30 | 22 | 22 | 0 | execute-phase orchestrator, L1 grep check |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-30
