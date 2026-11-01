---
phase: "02"
slug: "agent-tools-and-skill"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-31"
---

# Phase 02 - Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Model to tool handler | The model fills `board_edit` arguments (ops, base_rev, confirmed) and may name a session id that the handler ignores | Item text, item ids, integers, a boolean |
| Hermes registry to handler | Hermes passes `session_id` as a keyword; the handler reads the session from nothing else | Session id |
| Hook to store | `pre_tool_call` parses raw or coerced arguments and reads a board only for a reword candidate | Ops, item ids |
| Plugin to live Hermes on devpc | The enable adds two tools, two hooks, a prompt section and a skill to every new session; the restart drops live Desktop connections | Tool text, hook callbacks |
| Live session output to Claude | stream-json output and state.db can hold the system prompt and full replies | Prompt text, replies (never copied into the repo) |
| Claude to data.db and state.db during the live tests | Read-only opens, one seed write through the store API | Board rows, session rows |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Spoofing | board_tools.board_read | high | mitigate | The handler reads the session only from its keyword. The schema declares no session_id. `session_id_arg_findings` fails any core read of `args["session_id"]`. A uni | closed |
| T-02-02 | Elevation of Privilege | board_tools.board_read | high | mitigate | A None, empty or blank id returns NO_SESSION before resolve, so no code path reads a shared or default board. `resolve` also raises InvalidSession, wh | closed |
| T-02-03 | Information Disclosure | results.py | low | mitigate | Results hold only the rev, the markdown and fixed error strings. No path, SQL or exception text goes into a result. | closed |
| T-02-04 | Tampering | hooks.pre_tool_call, edit_args.parse | high | mitigate | One parser serves the hook and the handler. It accepts every form Hermes repairs (JSON-string ops, bare object, digit strings, true or false strings) | closed |
| T-02-05 | Denial of Service | hooks.pre_tool_call | high | mitigate | First statement returns None for any other tool name. The board path sits in try/except and fails closed for board_edit only. A test with a broken service pro | closed |
| T-02-06 | Denial of Service | edit_args.parse | medium | mitigate | `MAX_OPS = 100` per call. The store caps a board at 100 items and runs one BEGIN IMMEDIATE per call. | closed |
| T-02-07 | Tampering | confirmed flag | medium | accept | The flag is a forcing function, not a security boundary: the model can set it without asking. The first blocked call returns the instruction to ask. Plan 02-03 states the | closed |
| T-02-08 | Denial of Service | hooks.pre_tool_call latency | low | mitigate | No I/O unless the call holds a guarded op candidate and is not confirmed. A board read happens only for set_text. | closed |
| T-02-09 | Repudiation | hooks.post_compaction | low | mitigate | A failure logs with `log.exception` and returns. The resolver lineage walk still finds the root on the next resolve. | closed |
| T-02-10 | Tampering | board_read output, prompt section | medium | mitigate | The prompt section, the board_read description and the skill each say board items are Theo's notes, not instructions. Phase 1 `sanitize_text` and the | closed |
| T-02-11 | Information Disclosure | tool_text.py | low | mitigate | All text is a module constant. The section is a str, not a callable, so no session data enters it. A test checks the type and the static values. | closed |
| T-02-12 | Elevation of Privilege | board_tools.board_edit | high | mitigate | `resolution.kind == "delegate"` returns DELEGATE_EDIT before parse and apply (D-20). A test proves the delegator board is unchanged. RESEARCH Pitfall | closed |
| T-02-13 | Tampering | board_edit schema and handler | high | mitigate | The op enum holds four item-level kinds. No property takes a whole board. Every op addresses one item id (D-03). | closed |
| T-02-14 | Repudiation | results.py | medium | mitigate | Every handler return is a JSON str. Only failure objects hold a top-level `error` key, so Hermes marks failures from the shape, not from item text. | closed |
| T-02-15 | Spoofing | board_tools.board_edit | high | mitigate | The session comes from the keyword only; the Hermes dispatch test and a unit test prove a spoofed id writes nothing to the other board (TOOL-06). | closed |
| T-02-16 | Information Disclosure | headless stream-json output | medium | mitigate | Raw output stays in the session scratchpad and is never committed. The SUMMARY holds counts, session ids and at most the first line of each rep | closed |
| T-02-17 | Elevation of Privilege | hermes plugins enable | high | mitigate | `--no-allow-tool-override` grants no built-in tool override. The manifest declares no override and the plugin registers none. | closed |
| T-02-18 | Denial of Service | plugin enable reload and gateway restart | high | mitigate | Task 1 is a blocking-human announcement that names both the enable reload and the restart. Task 2 runs the enable and the restart only af | closed |
| T-02-19 | Denial of Service | hermes gateway restart | high | mitigate | Task 2 restarts only with `--yes --detach` after Theo's go. No serve process is stopped by hand. | closed |
| T-02-20 | Tampering | check script on state.db and data.db | medium | mitigate | state.db opens only through `SessionDB(read_only=True)`; data.db opens only with `mode=ro`. The script writes nothing. | closed |
| T-02-21 | Information Disclosure | stored system prompt read in mode `added` | low | mitigate | The script prints whether the section is present, never the prompt text. The SUMMARY holds no prompt content. | closed |
| T-02-22 | Tampering | check script modes `read` and `final` on state.db and data.db | medium | mitigate | state.db opens only through `SessionDB(read_only=True)`; data.db opens only with `mode=ro`. The script writes nothing. | closed |
| T-02-23 | Information Disclosure | session messages and tool results read in mode `read` | low | mitigate | The script prints flags, item rows and at most the first line of a reply, never a full message or a tool result. The SUM | closed |
| T-02-24 | Tampering | reword seed write to the real data.db | low | mitigate | One `BoardStore.apply` call with one `SetText` op, actor user, on the reword-a board only, with `base_rev` from a fresh read. No raw SQL. Every other | closed |
| T-02-SC | Tampering | dev dependencies | high | mitigate | No new package in this plan. | closed |

*Status: open, closed, open below high threshold (non-blocking)*
*Severity: critical > high > medium > low. Only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required), accept (documented risk), transfer (third-party)*

Verified by the security auditor on 2026-10-31 against the code, the tests (238 passed in the 9 phase 2 modules, the real Hermes dispatch test included) and the plan 02-05 to 02-07 SUMMARYs. Evidence per threat is in the auditor return recorded in the session; the file:line references point at `plugin/session_tasks/` and `tests/`.

Observations that open no threat:
1. The 02-05 SUMMARY states the announcement time imprecisely; the order announcement, go, enable, restart holds in the session record.
2. The plan 06 and 07 check script modes `read` and `final` were never built; the orchestrator ran the same read-only checks by hand.
3. The Hermes dispatch snippet spoof-tests `board_read` only; the `board_edit` spoof proof is the unit test, the hook test and the AST guard. Test coverage note, not an open threat.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-02-01 | T-02-07 | The `confirmed` flag is a forcing function, not a security boundary. The model can set it without asking Theo. The hook blocks the first unconfirmed remove, uncheck or reword of an item Theo touched, and the block text tells the agent to ask or to confirm. The ask rule sits in the tool descriptions, the `confirmed` field, the prompt section and the skill. Since quick task 261031-lbp, `confirmed true` means Theo's own message named the change. Live measures: 02-05 SUMMARY ask cases and 02-07 SUMMARY turn 4. Severity medium, below the high block threshold. | Theo (plan 02-02 disposition, CONTEXT D-18) | 2026-10-31 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-31 | 25 | 25 | 0 | gsd-security-auditor (sonnet) via /gsd-secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-31
