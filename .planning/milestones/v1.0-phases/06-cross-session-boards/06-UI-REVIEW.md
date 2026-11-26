# Phase 6 - UI Review

**Audited:** 2026-11-02
**Baseline:** 06-UI-SPEC.md (approved 2026-11-02), extending 04-UI-SPEC.md
**Screenshots:** not captured (static audit by constraint; the pane renders only inside Hermes Desktop on the Mac). A Vite server answered on localhost:5173, but it belongs to another project and cannot render this pane. The visual evidence is Theo's five Mac checks in 06-12-SUMMARY.md Task 4, all passed.
**Interaction captures:** off (workflow.ui_interaction_capture is false)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every new string in the contract is in the file, character for character. |
| 2. Visuals | 3/4 | The banner has square corners next to rounded SDK controls; the spec row layout line restates a Phase 4 layout that Phase 4 changed. |
| 3. Color | 4/4 | Exactly the five theme variables of the contract, no literal, no palette class, no new accent use. |
| 4. Typography | 4/4 | Two sizes (`text-xs` 9, `text-sm` 1) and one set weight (`font-medium` 2), as declared. |
| 5. Spacing | 4/4 | Every class is on the 4px scale; the two inline widths (304px, 320px) are the two declared exceptions. |
| 6. Experience Design | 3/4 | Every state in the contract is handled, but the notice line is silent to a screen reader and Back drops keyboard focus. |

**Overall: 22/24**

---

## Top 3 Priority Fixes

1. **The notice line has no live region** - a screen reader never hears `Copied 1 to ...` or `Could not save that change.` - add `role: 'status'` to the `div` in `Notice` (plugin.js:366 and :367). One attribute, no layout change.
2. **Back drops keyboard focus** - `back()` (plugin.js:1188) unmounts the Back button that holds focus, so focus falls to the document body and the next Tab starts from the top - after `setPicked(null)` move focus to the picker trigger (a ref on the trigger `Button`, `focus()` in a `useEffect` keyed on `picked`).
3. **Banner corners and a stale spec line** - the banner `div` (plugin.js:102) draws a 1px square border while the sketch draws a 6px radius and every SDK control beside it is rounded - add `rounded-md` to `BANNER_CLASS`, and change 06-UI-SPEC.md line 94 to the Phase 4 layout as built (checkbox first, chevron after the text, 04-08-SUMMARY.md).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

Checked every string in the Copywriting Contract against `plugin/desktop/plugin.js`.

| Contract string | File | Match |
|-----------------|------|-------|
| `Choose a session` | `PICKER_TIP` line 72 | yes |
| `Untitled session` and `Untitled session {short id}` | `UNTITLED` line 73, `boardLabel` line 171 | yes |
| `No other session has a board.` | line 74 | yes |
| `Could not load the session list. Reopen the list to retry.` | line 75 | yes |
| `Read only. Viewing another session.` | line 76 | yes |
| `Back`, aria `Back to {focused label}` | lines 77, 530 | yes |
| `This board is empty.` / `Pick another session or go back.` | lines 78, 79 | yes |
| `this session`, joined with ` - ` | lines 80, 183 | yes |
| `Copy`, aria `Copy item to {focused label}` | lines 81, 82, 1233 | yes |
| `Copy all open to {focused label}` | line 83, 1229 | yes |
| `Session: {label}, {open} of {total} open` and the total 0 form | `pickerAriaLabel` line 229 | yes |
| `Copied {N} to {label}. {M} skipped, already on the board.` plus the cap clause only above 0 | `copyNoticeText` line 340 | yes |
| Time labels `just now`, `{n} min ago`, `today HH:mm`, `Mon D`, `Mon D, YYYY` | `updatedLabel` line 215 | yes |
| Stale and write failed reuse for the copy reply | `runCopy` lines 969 to 975 | yes |

Phase 4 strings are unchanged (lines 35 to 46). Mac check 5 saw the full D-42 sentence with `0 skipped, already on the board.` in the real pane.

Minor (no score impact): the picked board load failure shows the Phase 4 line `Could not load the board. Retrying.` with no word that it is the other board. The contract chose this reuse (Interaction Contract, Read-only view 8).

### Pillar 2: Visuals (3/4)

- Focal point as declared: the picker title is the one 14px / 500 text (`PICKER_TITLE_CLASS` line 95) and sits first (line 1256). The banner is the second anchor in the read-only view (line 1266). Mac checks 2 and 4 confirm both read as intended.
- Icon-only controls carry an aria-label and a Tip: chevron (line 549), plus and trash (`RowButton` line 564), markdown `CopyButton` (label line 403). The shown board in the menu is marked by `icons.Check` plus `aria-current` (lines 419, 436), as rule 2 asks.
- WARNING: `BANNER_CLASS` (line 102) sets `border border-(--ui-yellow) px-2 py-1` and no corner radius. The approved sketch draws the banner with `border-radius: 6px` (sketch line 31). The SDK `outline` picker button above it and the `Button` beside it are rounded. The spec is silent on the radius, so this is a spec gap and a visual seam, not a contract break. Fix: `rounded-md` in `BANNER_CLASS`.
- WARNING: 06-UI-SPEC.md line 94 says the read-only row starts with a 24px chevron column, "empty when no subtasks". The file renders the checkbox first and the chevron after the text, only when subtasks exist (`ItemRow` lines 602 to 617). That is the Phase 4 layout Theo asked for on the built page (04-08-SUMMARY.md line 89). The code is right and the spec line is stale. Fix the spec line, not the code.
- The row Copy button is revealed on hover or focus-within and keeps its space (`ROW_COPY_CLASS` line 92, test `test_row_copy_keeps_its_space`). Mac check 4 saw "Copy on hover".

### Pillar 3: Color (4/4)

Grep over `plugin/desktop/plugin.js`:

| Token | Count | Contract use |
|-------|-------|--------------|
| `(--ui-text-secondary)` | 6 | done text, counts, notice, menu sub-lines and right block |
| `(--ui-text-tertiary)` | 1 | checkbox border |
| `(--ui-stroke-secondary)` | 1 | header hairline |
| `(--ui-text-primary)` | 1 | banner text |
| `(--ui-yellow)` | 1 | banner border |

- Hex, `rgb(`, `color-mix` and Tailwind palette classes: 0 hits. Tests `test_plugin_has_no_colour_literal`, `test_class_names_carry_no_palette_colour` and `test_banner_uses_only_the_yellow_border_token` pin this.
- Accent: the pane writes none. The Copy all open button is `variant: 'outline'` (line 384), not the sketch's accent blue, as the contract decided (Color, default 4).
- Banner has no fill (rule 1). The read-only state is carried by text, not by colour alone.

### Pillar 4: Typography (4/4)

- Sizes: `text-xs` 9 uses, `text-sm` 1 use (the picker title). Weights: `font-medium` 2 uses (picker title line 95, menu row name line 99). Nothing else sets a size or weight.
- Truncation style is one shared object `TRUNCATE_STYLE` (line 89) on the picker title, the menu name and sub-line, the Copy all open label and the copied notice title piece. Counts carry `NOWRAP_STYLE` and `shrink-0`. Test `test_truncation_styles` runs a 60 character, a 10 character and an empty title.
- Item text keeps the Phase 4 wrap style (`TEXT_STYLE` line 69) and never truncates.

### Pillar 5: Spacing (4/4)

Class counts: `py-1` 5, `px-2` 3, `mt-2` 3, `pt-2` 2, `pl-6` 2, `p-2` 2, `gap-1` 2, `mx-2` 1, `gap-2` 1. All on the 4px scale. No arbitrary `[Npx]` class.

| Contract item | File | Match |
|---------------|------|-------|
| Picker row `px-2 pt-2` | `PICKER_ROW_CLASS` line 93 | yes |
| Trigger `min-h-8 w-full justify-between` | line 94 | yes |
| Menu width 304px inline | `MENU_STYLE` line 87 | yes |
| Banner `mx-2 mt-2`, 1px border, `px-2 py-1` | line 102 | yes |
| Header row `gap-2 p-2` with the hairline | line 49 | yes |
| Vertical order picker, banner, header, notice, list | lines 1256 to 1279 | yes |
| Pane width 320px | registration line 1329 | yes |
| Check slot and caret `size-4 shrink-0` | `CARET_CLASS` line 97 | yes |

Minor (no score impact): the banner is a plain `div` and gets the pane's default line height, so its height depends on the SDK `inline` Back button. The Mac check saw one line.

### Pillar 6: Experience Design (3/4)

State coverage against the UI Considerations table:

| State | Handled at | Evidence |
|-------|------------|----------|
| Menu: only the focused board | `PickerMenu` line 448 | `test_only_the_focused_board_gives_the_no_other_line` |
| Menu: `GET /boards` fails, reopen retries | lines 446, 887 | `test_boards_failure_gives_the_list_failed_line_and_reopen_retries` |
| `session.list` fails: fallback labels, no error text | `loadTitles` line 863 | `test_session_list_failure_keeps_fallback_labels_and_no_error_line` |
| Picked board empty | line 1245 | `test_empty_picked_board_shows_its_empty_state` |
| Picked board load fails, poll retries | `reloadPicked` line 853 | `test_picked_board_load_failure_shows_the_notice_and_retries` |
| Copy in flight disables every copy control | lines 636, 1273 | `test_double_click_sends_one_copy` |
| Copy stale or failed | lines 969 to 975 | two tests in `test_pane_copy.py` |
| Focus change during a copy | line 968 | `test_focus_change_during_a_copy_keeps_its_session` |
| Event root match, poll fallback | lines 1036 to 1044 | five tests in `test_pane_readonly.py` |
| Open edit saved before a pick | `pick` line 1202 | `test_an_open_edit_is_saved_before_a_pick` |
| No write control in the read-only view | `ItemRow` lines 609 to 648 | `test_read_only_view_sends_no_write` |

Mac check 5 proves the copy end to end: the notice, the item on the focused board unchecked, the source board unchanged.

- WARNING: the notice `div` (`Notice` lines 366, 367) has no `role="status"` and no `aria-live`. The copy result, the stale notice and the write failed notice are the only feedback of a copy, and a screen reader hears none of them. This is a Phase 4 gap that Phase 6 widens, because the copy has no other visible result on the shown board. Fix: `role: 'status'` on the notice `div`.
- WARNING: `back()` (line 1188) removes the banner that holds the focused Back button. Focus falls to the document body. A keyboard user Tabs from the top of the window again. Fix: focus the picker trigger after Back. The menu path is SDK-owned and returns focus to the trigger on its own (Interaction Contract, picker menu 10).
- Minor: between a pick and the first `GET /board` reply the list area is blank (line 1245 keeps `isEmpty` false until `pickedServer` arrives). The contract chose no skeleton (Component Inventory, "Not used"). On a local gateway the gap is one round trip.
- Minor: a disabled row Copy button cannot take focus, so during a copy a keyboard user loses the focus-within reveal on that row until the copy settles. Transient, one request long.
- Destructive actions: none in this phase, no confirm needed (contract note 7). The Phase 4 `ConfirmDialog` is not rendered in the read-only view (line 1316 renders it, but `onDelete` is not in `readOnlyActions`, so it never opens).

Registry audit: no `components.json`, no shadcn, no third-party registry. Skipped.

---

## Files Audited

- `/home/theo/local_repo/hermes-session-tasks/plugin/desktop/plugin.js` (1342 lines, the one pane file)
- `/home/theo/local_repo/hermes-session-tasks/.planning/phases/06-cross-session-boards/06-UI-SPEC.md`
- `/home/theo/local_repo/hermes-session-tasks/.planning/phases/04-pane/04-UI-SPEC.md` (the extended contract)
- `/home/theo/local_repo/hermes-session-tasks/.planning/phases/06-cross-session-boards/06-CONTEXT.md`
- `/home/theo/local_repo/hermes-session-tasks/.planning/sketches/06-session-picker.html`
- `/home/theo/local_repo/hermes-session-tasks/.planning/phases/06-cross-session-boards/06-01-SUMMARY.md` to `06-12-SUMMARY.md` and `06-09-PLAN.md` to `06-12-PLAN.md`
- `/home/theo/local_repo/hermes-session-tasks/.planning/phases/04-pane/04-08-SUMMARY.md` (chevron position decision)
- `/home/theo/local_repo/hermes-session-tasks/tests/test_pane_picker.py`, `tests/test_pane_readonly.py`, `tests/test_pane_copy.py`, `tests/test_desktop_plugin.py` (test names and the colour checks)
- No `04-UI-REVIEW.md` exists; `04-REVIEW.md` is a code review, so this file follows the gsd-ui-auditor output shape.
