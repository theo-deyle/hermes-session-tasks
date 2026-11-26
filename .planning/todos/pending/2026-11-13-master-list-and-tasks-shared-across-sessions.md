---
created: 2026-11-13T19:09:13Z
title: Master list and tasks shared across sessions
area: general
severity: minor
files: []
---

## Problem

Theo asked for this on 2026-11-13. It is a feature for a later milestone, not a defect.

- Theo wants one master list that shows the tasks of all sessions.
- Each task has an id (a UUID) that Theo can copy. The id ties the task to its home session.
- Theo quotes that id in another session. The task then shows on the board of that session too.
- The board marks such a task as a task from one or more other sessions.
- When the task is completed or updated in one session, the change shows in every session that holds it.

## Solution

TBD. Hints:

- One task record with many board memberships, not one copy for each board. A copy cannot stay in step.
- Phase 6 (cross-session boards) already lets the pane open the board of another session. Start from that code.
- Decide in the discussion: who may edit a shared task, and what a delete does in a session that is not the home session.
- Related: 2026-11-13-configurable-checkbox-states-and-workflow.md (the state "in progress in another session").
