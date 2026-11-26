---
phase: 01-core-storage-and-session-identity
reviewed: 2026-10-30T18:00:00Z
depth: standard
files_reviewed: 36
files_reviewed_list:
  - plugin/session_tasks/__init__.py
  - plugin/session_tasks/aliases.py
  - plugin/session_tasks/db.py
  - plugin/session_tasks/fork.py
  - plugin/session_tasks/lineage.py
  - plugin/session_tasks/markdown.py
  - plugin/session_tasks/model.py
  - plugin/session_tasks/paths.py
  - plugin/session_tasks/revision.py
  - plugin/session_tasks/rows.py
  - plugin/session_tasks/schema.py
  - plugin/session_tasks/session_reader.py
  - plugin/session_tasks/store.py
  - pyproject.toml
  - scripts/check.sh
  - scripts/check_pins.py
  - tests/conftest.py
  - tests/fakes.py
  - tests/fork_race_worker.py
  - tests/hermes_contract_snippet.py
  - tests/home_guard.py
  - tests/race_worker.py
  - tests/test_adapters.py
  - tests/test_fork.py
  - tests/test_hermes_contract.py
  - tests/test_layout.py
  - tests/test_lineage.py
  - tests/test_markdown.py
  - tests/test_markdown_roundtrip.py
  - tests/test_phase_flow.py
  - tests/test_race.py
  - tests/test_store_items.py
  - tests/test_store_revision.py
  - tests/test_store_subtasks.py
  - tests/test_tracer.py
findings:
  critical: 1
  warning: 3
  info: 6
  total: 10
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-10-30T18:00:00Z
**Depth:** standard
**Files Reviewed:** 36
**Status:** issues_found

## Summary

The core is small and clean. Writes use one `BEGIN IMMEDIATE` per operation on a fresh connection. The migration re-reads `user_version` inside the lock. All SQL is parameterised. The code has no 3.12+ syntax. The only Hermes imports are `plugins.plugin_storage` and `hermes_state`, both lazy and both on the allowlist. The suite passes (197 tests on Python 3.11) and `ruff check` is clean.

The review found one real behaviour defect in session identity. A branch that is compressed before its board is first touched never gets the copy of its parent board (CR-01). A delegate session that is compressed gets a different board from the one its delegator uses (WR-01). The store layer accepts a blank session key (WR-02). The test guard for the real `~/.hermes` home cannot see a write to a file that already exists (WR-03).

I confirmed CR-01, WR-01 and WR-02 with throwaway tests built on `FakeReaderFactory`. The probe files are removed and the tree is clean.

## Critical Issues

### CR-01: A compressed branch never gets the copy of its parent board (BLOCKER)

**File:** `plugin/session_tasks/lineage.py:184-192` and `plugin/session_tasks/lineage.py:132-149`
**Issue:** D-06 says a branch starts with a copy of its parent board on its first touch. The copy runs only in `_branch`, which `_resolve` reaches only when `is_explicit_fork_child(session_id)` is true for the id being resolved.

Hermes copies `model_config` onto a compression child. Hermes counts a marker only when it equals `parent_session_id` (`hermes_state_messages.py:1878-1897`). So the compression child `br2` of a branch `br` is not an explicit fork child. `_resolve("br2")` goes to `_compression`. `get_compression_lineage("br2")` returns `["br", "br2"]`, so the root is `br`. The code returns `Resolution("br", "compression")` and never calls `fork_copy` for `br`.

The result: if the branch is compressed before anything touches its board, the agent and the pane read and write an empty board. The parent items are lost to the branch with no error.

The second path is `record_compaction`. When the hook runs for `(br2, br)`, `_root_of_old` returns `br` and the alias `br2 -> br` is stored. Every later `resolve("br2")` is an alias hit, so `fork_copy` never runs.

Probe result, using the seven-row fixture with `br` marked as compressed and a child `br2`, and a parent board holding one item:

```
RES Resolution(root_id='br', kind='compression', forked_from=None)
BOARD Board(root_id='br', rev=0, next_item_id=1, items=(), forked_from=None)
```

No test covers a compressed branch. `tests/test_fork.py` covers a branch of a compression tip and a branch of a branch, but not a compression child of a branch.

**Fix:** In `_compression`, after the lineage root is known, resolve the root as a possible branch before the alias write. In `record_compaction`, do the same before `put_alias`. For example:

```python
def _compression(self, session_id, reader, walk):
    lineage = reader.get_compression_lineage(session_id)
    root_id = lineage[0] if lineage else session_id
    if root_id == session_id:
        return Resolution(session_id, "plain")
    self._ensure_branch_copy(root_id, reader, walk)   # new: fork_copy when root is a branch child
    ...

def _ensure_branch_copy(self, root_id, reader, walk):
    row = reader.get_session(root_id)
    if row is None or not reader.is_explicit_fork_child(root_id):
        return
    branched = _branched_from(row)
    if branched:
        walk.visit(root_id)
        parent_root = self._resolve(branched, walk).root_id
        fork_copy(self.connect, root_id, parent_root, self.clock)
```

Add a test in `tests/test_fork.py`: a branch that is compressed before its first touch, resolved through the tip and through `record_compaction`, must show the parent items.

## Warnings

### WR-01: A compressed delegate session writes to a board that its delegator does not use

**File:** `plugin/session_tasks/lineage.py:155-161`
**Issue:** `resolve("dg")` returns the delegator root (`kind="delegate"`), as the docstring promises. But `record_compaction("dg2", "dg")` calls `_root_of_old("dg")`. For a delegate, `get_compression_lineage("dg")` returns `["dg"]` (it is an explicit fork child), so the alias becomes `dg2 -> dg`. Probe result:

```
DG  Resolution(root_id='root', kind='delegate', forked_from=None)
DG2 Resolution(root_id='dg', kind='compression', forked_from=None)
```

After a compaction, the subagent's board key changes from the delegator's root to the delegate's own id. The subagent then stops seeing the board the delegator uses. The "never a shared key" rule holds, but the resolver gives two answers for one conversation.

**Fix:** Make `_root_of_old` resolve the old id with `_resolve` when no alias is known, and use `.root_id` of that result. This handles plain, compression, branch and delegate with one rule. Add a test for a delegate compaction.

### WR-02: `BoardStore` accepts a blank or whitespace session key

**File:** `plugin/session_tasks/store.py:191-212` (`get_board`, `apply`) and `plugin/session_tasks/store.py:223-227`
**Issue:** The blank-key guard lives only in `SessionResolver._check_id`. `BoardStore.apply("")` and `BoardStore.apply("  ")` both return `Applied` and create a board with that key plus an alias `"" -> ""`. Probe result: both calls returned `Applied`. Every caller that passes an empty string, for example from a bad tool argument or a missing `session_id` default, then shares one board. Project rules call a blank or shared key a security defect. The store is the last layer before the file, and Phase 2 and Phase 3 code will call it.

**Fix:** Validate `root_id` at the top of `apply` and `get_board`. Reuse one check from `model.py`:

```python
def check_session_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidSession("session id must be a non-empty string")
    return value
```

Call it from `lineage._check_id` and from both `BoardStore` entry points. Add a store test for `""`, `"  "` and a non-string key.

### WR-03: The real-home guard cannot see a write to an existing file

**File:** `tests/home_guard.py:33-67`
**Issue:** The session guard compares entry names only. It fails the run when a new directory or file appears under the real `~/.hermes/plugin-data/hermes-session-tasks`. After the first production deploy, `data.db` and the directory exist in the real home. A test that opens and writes the real `data.db` then adds no new name, so the guard passes. `snapshot` also skips `-wal`, `-shm` and `-journal` names. The guard therefore protects only the first run on a fresh machine. The task asked specifically for any test that could touch the real `~/.hermes` to be a finding.

**Fix:** Record `(size, mtime_ns)` for each existing entry and flag a changed entry as well as a new one. Keep the sidecar skip for names only, and compare `data.db` itself:

```python
entries[rel] = (stat.st_size, stat.st_mtime_ns)   # snapshot value becomes dict[str, tuple[int, int]]
```

Update `new_entries` to return names that are new or whose tuple changed, and extend `tests/test_layout.py` with a case that rewrites an existing `data.db`.

## Info

### IN-01: Session id whitespace is handled in two ways

**File:** `plugin/session_tasks/lineage.py:77-80` and `plugin/session_tasks/lineage.py:137-138`
**Issue:** `_check_id` validates with `strip()` but returns the unstripped id. `record_compaction` strips `old_session_id` but not `session_id`. The ids `"abc"` and `" abc"` are two boards. Hermes ids carry no padding, so this is not exploitable today.
**Fix:** Pick one rule. Either reject ids that differ from their stripped form, or return the stripped id from `_check_id` and use it everywhere.

### IN-02: Duplicate row mapping in `rows.py`

**File:** `plugin/session_tasks/rows.py:35-51` and `plugin/session_tasks/rows.py:109-120`
**Issue:** `read_items` builds an `Item` inline. `_item_from_row` builds the same `Item` from the same column list. The two copies can drift when a column is added.
**Fix:** Make `read_items` call `_item_from_row` and delete the inline copy.

### IN-03: The store does not check the type of operation fields

**File:** `plugin/session_tasks/store.py:105-127`, `plugin/session_tasks/rows.py:72-86`
**Issue:** `AddItem(checked=2)` reaches the `CHECK (checked IN (0, 1))` constraint and raises a raw `sqlite3.IntegrityError`. A non-string `text` raises `TypeError` or `AttributeError` inside `sanitize_text`. Both abort the transaction safely, but the caller gets an error type outside the `BoardError` family. Phase 2 and Phase 3 should validate at their boundary, so this is a robustness note for the store contract.
**Fix:** In `clean_text`, raise `EmptyText` or a new `BadOperation` for a non-string. Coerce or reject non-bool `checked` in `_add` and `_set_checked`.

### IN-04: The `moved` count and the promotion rule disagree for lines under a skipped parent

**File:** `plugin/session_tasks/markdown.py:128-141`
**Issue:** A line under a skipped top-level line (empty or over 500 characters) becomes a top-level item. At depth 1 the line is promoted and not counted in `moved`. At depth 2 or more the line is promoted to top level, yet `moved` counts it as "moved up to the subtask level". The import result then reports a figure that matches neither case. The docstring of `_build_tree` states the promotion but D-02 states only the move-up rule.
**Fix:** Count every promotion the same way, or count promotions in their own field of `ParseResult`. Add a test for a nested block under an empty parent line.

### IN-05: Text made only of invisible characters passes the empty check

**File:** `plugin/session_tasks/model.py:21-24` and `plugin/session_tasks/model.py:170-184`
**Issue:** `sanitize_text` drops categories Cc, Cf, Cs and Co. Characters such as U+3164 (Hangul filler, category Lo) and U+2800 (braille blank, category So) stay. An item made of those characters passes `clean_text` and shows as a blank row in the pane and in the agent view.
**Fix:** After sanitising, also reject text where every character is in a short deny list of blank-looking code points, or test `char.isprintable()` plus a visible-glyph set. Add a test for U+3164 and U+2800.

### IN-06: `check_pins.py` parses pip output with no guard and skips quietly

**File:** `scripts/check_pins.py:86` and `scripts/check_pins.py:121-129`
**Issue:** `json.loads(result.stdout)` raises an uncaught `JSONDecodeError` if `pip list` prints anything else on stdout. A missing Hermes checkout, a missing gateway venv, or a timed-out `pip list` each print a "skip:" line and the script still exits 0, so `check.sh` reports "all ok" with the gateway comparison not done. The `skip` is visible in the output but the exit code does not show it.
**Fix:** Wrap `json.loads` in a `try` for `ValueError` and return the same `(None, reason)` pair. Add an environment switch (for example `REQUIRE_GATEWAY=1`) that turns a skip into exit code 1, and set it in the deploy check.

---

_Reviewed: 2026-10-30T18:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
