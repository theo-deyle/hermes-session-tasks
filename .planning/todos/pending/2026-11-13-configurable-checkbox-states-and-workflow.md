---
created: 2026-11-13T19:09:13Z
title: Configurable checkbox states and workflow
area: general
severity: minor
files: []
---

## Problem

Theo asked for this on 2026-11-13. It is a feature for a later milestone, not a defect.

- A task has only two states today: open and done.
- Theo wants more checkbox states, and he wants to configure them.
- The models are the Task Genius and TaskNotes plugins of Obsidian: a workflow changes the checkbox by type of work or by status.
- States Theo named: blocked (something holds him back), scheduled (show the date), cancelled, in progress in another session. The list is open.

## Solution

TBD. Hints:

- A status field on the task replaces the done flag. Each status has a mark, a label and a "counts as done" flag.
- The scheduled state needs a date on the task.
- The markdown import and export need a rule for each mark (Obsidian uses `[/]`, `[-]`, `[>]`, `[!]`).
- A UI choice gets a sketch under `.planning/sketches/` before the decision.
- Related: 2026-11-13-master-list-and-tasks-shared-across-sessions.md.
