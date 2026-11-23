/**
 * Session tasks pane for hermes-session-tasks. Plain ESM, loaded uncompiled: UI is jsx() calls.
 * Only three imports resolve here: the plugin SDK, react and the jsx runtime.
 * It shows the focused session's board as checkbox rows and sends the user's edits through the plugin routes.
 * Only Pane calls React hooks. Every other component is a plain function of its props.
 */

import {
  Button,
  Checkbox,
  Codicon,
  ConfirmDialog,
  CopyButton,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  EmptyState,
  Input,
  PALETTE_AREA,
  ScrollArea,
  Tip,
  host,
  icons,
  useValue
} from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const PLUGIN_ID = 'hermes-session-tasks'
const PLUGIN_VERSION = '0.2.0'
const API_VERSION = 1
const POLL_MS = 6000
const NOTICE_MS = 4000
const EVENT_TYPE = 'plugin.hermes-session-tasks.board.updated'
const PANE_KEY = 'pane'
// Desktop scopes a contributed pane id as `<pluginId>:<paneId>`.
const PANE_ID = `${PLUGIN_ID}:${PANE_KEY}`
const SHOW_LABEL = 'Tasks'
const SHOW_TITLE = 'Show the Session tasks pane'
const SHOW_TOGGLE_LABEL = 'Session tasks'
const SHOW_COMMAND = 'Show Session tasks'
const SHOW_ICON = 'checklist'
const SHOW_ORDER = 90
const MISMATCH_LINE = 'Version mismatch: update the desktop plugin on this machine'
const STALE_NOTICE = 'Board changed, showing the latest'
const WRITE_FAILED_NOTICE = 'Could not save that change. Try again.'
const LOAD_FAILED_NOTICE = 'Could not load the board. Retrying.'
const EMPTY_TITLE = 'The agent adds items here.'
const EMPTY_HINT = 'Add one below.'
const NO_CHAT_TITLE = 'Open a chat to see its items.'
const ADD_PLACEHOLDER = 'Add an item'
const SUBTASK_PLACEHOLDER = 'Add a subtask'
const CONFIRM_TITLE = 'Delete this item?'
const CONFIRM_LABEL = 'Delete item and subtasks'
const CANCEL_LABEL = 'Keep item'
const MAX_TEXT_CHARS = 500
const PANE_CLASS = 'flex h-full flex-col text-xs'
const HEADER_ROW_CLASS =
  'flex items-center justify-end gap-2 border-b border-(--ui-stroke-secondary) p-2'
const NOTICE_CLASS = 'px-2 pt-2 text-xs text-(--ui-text-secondary)'
const ROW_CLASS = 'group flex min-h-8 items-start gap-1 py-1'
const SUBTASK_ROW_CLASS = 'group flex min-h-8 items-start gap-1 py-1 pl-6'
const COUNT_CLASS = 'shrink-0 py-1 text-xs text-(--ui-text-secondary)'
const LIST_CLASS = 'min-h-0 flex-1'
const LIST_BODY_CLASS = 'flex flex-col p-2'
const ADD_LINE_CLASS = 'mt-2'
const SUBTASK_LINE_CLASS = 'mt-2 pl-6'
// The plus and trash buttons keep their space at all times and shows on row hover or keyboard focus in the row.
const REVEAL_CLASS = 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100'
const ROW_BUTTON_CLASS = `${REVEAL_CLASS} shrink-0`
const ESCAPED_HASH = /^\\*#[0-9]+(?:\s|$)/
const HIT_CLASS = 'flex size-6 shrink-0 items-center justify-center'
// The SDK box border fades into the dark theme; the tertiary text colour keeps it visible.
const CHECK_CLASS = 'border-(--ui-text-tertiary)'
const TEXT_CLASS = 'min-w-0 flex-1 py-1 text-xs'
const EDIT_CLASS = 'min-w-0 flex-1'
const DONE_CLASS = 'text-(--ui-text-secondary)'
const TEXT_STYLE = { overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }
const DONE_STYLE = { ...TEXT_STYLE, textDecoration: 'line-through' }
const NOTICE_STYLE = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }
const PICKER_TIP = 'Choose a session'
const UNTITLED = 'Untitled session'
const NO_OTHER_BOARDS = 'No other session has a board.'
const LIST_FAILED = 'Could not load the session list. Reopen the list to retry.'
const READ_ONLY_BANNER = 'Read only. Viewing another session.'
const BACK_LABEL = 'Back'
const READ_ONLY_EMPTY_TITLE = 'This board is empty.'
const READ_ONLY_EMPTY_HINT = 'Pick another session or go back.'
const THIS_SESSION = 'this session'
const COPY_LABEL = 'Copy'
const COPY_ROW_ARIA = 'Copy item to '
const COPY_ALL_PREFIX = 'Copy all open to '
const BOARD_CAP = 100
const SESSION_LIST_LIMIT = 200
const SHORT_ID_CHARS = 6
const MENU_STYLE = { width: '304px' }
// A one-line text that ends with an ellipsis. A count never wraps and never shrinks.
const TRUNCATE_STYLE = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }
const NOWRAP_STYLE = { whiteSpace: 'nowrap' }
const COPIED_NOTICE_STYLE = { ...NOTICE_STYLE, display: 'flex' }
const ROW_COPY_CLASS = `${REVEAL_CLASS} shrink-0`
const PICKER_ROW_CLASS = 'px-2 pt-2'
const PICKER_BUTTON_CLASS = 'min-h-8 w-full justify-between'
const PICKER_TITLE_CLASS = 'min-w-0 flex-1 text-sm font-medium'
const PICKER_COUNT_CLASS = 'shrink-0 text-xs text-(--ui-text-secondary)'
const CARET_CLASS = 'size-4 shrink-0'
const MENU_LEFT_CLASS = 'flex min-w-0 flex-1 flex-col'
const MENU_NAME_CLASS = 'text-xs font-medium'
const MENU_SUB_CLASS = 'text-xs text-(--ui-text-secondary)'
const MENU_RIGHT_CLASS = 'flex shrink-0 flex-col text-right text-xs text-(--ui-text-secondary)'
const BANNER_CLASS =
  'mx-2 mt-2 flex items-center justify-between rounded-md border border-(--ui-yellow) px-2 py-1 text-xs text-(--ui-text-primary)'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const MS_PER_MINUTE = 60000
const MS_PER_HOUR = 3600000

function isTopLevel(item) {
  return item.parent_id === null || item.parent_id === undefined
}

// A pending item has no id yet, so its key and its row id come from the pending key.
function isPending(item) {
  return item.id === null
}

function itemKey(item) {
  return isPending(item) ? item.pendingKey : item.id
}

function rowId(item) {
  return isPending(item) ? 'pending' : String(item.id)
}

function boardItems(board) {
  return board && Array.isArray(board.items) ? board.items : []
}

function openCounts(items) {
  const open = items.filter(item => !item.checked).length
  return { open, total: items.length }
}

function headerText(counts) {
  return `${counts.open} of ${counts.total} open`
}

// The last 6 characters of a board root id. A Hermes id starts with a date, so the end tells boards apart.
function shortId(rootId) {
  return String(rootId).slice(-SHORT_ID_CHARS)
}

function rowTitle(row) {
  for (const field of [row.title, row.preview]) {
    if (typeof field === 'string' && field.trim() !== '') return field
  }
  return null
}

// Maps a board root id to its Hermes label: the title, else the preview. The first row for a root wins.
// A session that was never compressed has a null lineage root, so its own id is the key.
function titleMap(rows) {
  const titles = {}
  const seen = new Set()
  for (const row of Array.isArray(rows) ? rows : []) {
    if (row === null || typeof row !== 'object') continue
    const root = row._lineage_root_id ?? row.id
    if (typeof root !== 'string' || root === '' || seen.has(root)) continue
    seen.add(root)
    const label = rowTitle(row)
    if (label !== null) titles[root] = label
  }
  return titles
}

function hasTitle(rootId, titles) {
  return Object.hasOwn(titles, rootId)
}

// The single-line label of a board: the trigger, the aria-label and later the notices.
function boardLabel(rootId, titles) {
  return hasTitle(rootId, titles) ? titles[rootId] : `${UNTITLED} ${shortId(rootId)}`
}

function menuName(rootId, titles) {
  return hasTitle(rootId, titles) ? titles[rootId] : UNTITLED
}

function menuSubLine(rootId, focusedRoot, titles) {
  const parts = []
  if (rootId === focusedRoot) parts.push(THIS_SESSION)
  if (!hasTitle(rootId, titles)) parts.push(shortId(rootId))
  return parts.length === 0 ? null : parts.join(' - ')
}

function updatedMs(board) {
  const ms = typeof board.updated_at === 'string' ? Date.parse(board.updated_at) : Number.NaN
  return Number.isNaN(ms) ? null : ms
}

// The focused board comes first. The others follow, newest update first. A board with no time goes last.
// Equal times sort by root id. `focused` is the focused entry of the list, or null when the list lacks it.
function orderBoards(boards, focusedRoot) {
  const list = Array.isArray(boards) ? boards.filter(board => board && board.root_id) : []
  const others = list.filter(board => board.root_id !== focusedRoot)
  others.sort((a, b) => {
    const left = updatedMs(a)
    const right = updatedMs(b)
    if (left !== right) {
      if (left === null) return 1
      if (right === null) return -1
      return right - left
    }
    if (a.root_id === b.root_id) return 0
    return a.root_id < b.root_id ? -1 : 1
  })
  return { focused: list.find(board => board.root_id === focusedRoot) ?? null, others }
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

// The update time of a board as a short English label. Null when the time is absent or unreadable.
function updatedLabel(iso, nowMs) {
  const then = typeof iso === 'string' ? Date.parse(iso) : Number.NaN
  if (Number.isNaN(then)) return null
  const diff = nowMs - then
  if (diff < MS_PER_MINUTE) return 'just now'
  if (diff < MS_PER_HOUR) return `${Math.floor(diff / MS_PER_MINUTE)} min ago`
  const when = new Date(then)
  const now = new Date(nowMs)
  const day = `${MONTHS[when.getMonth()]} ${when.getDate()}`
  if (when.getFullYear() !== now.getFullYear()) return `${day}, ${when.getFullYear()}`
  if (when.getMonth() !== now.getMonth() || when.getDate() !== now.getDate()) return day
  return `today ${pad2(when.getHours())}:${pad2(when.getMinutes())}`
}

function pickerAriaLabel(label, counts) {
  return counts.total === 0 ? `Session: ${label}` : `Session: ${label}, ${headerText(counts)}`
}

// Groups the board items by parent. Items arrive in board order, each subtask after its parent.
// A subtask whose parent is missing stays visible as a top-level entry.
function buildTree(items) {
  const groups = []
  const byId = new Map()
  for (const item of items) {
    const parent = isTopLevel(item) ? undefined : byId.get(item.parent_id)
    if (parent) {
      parent.children.push(item)
    } else {
      const group = { item, children: [] }
      groups.push(group)
      byId.set(item.id, group)
    }
  }
  return groups
}

function subtaskCountText(children) {
  const done = children.filter(child => child.checked).length
  return `${done}/${children.length}`
}

// The copy text: one checklist line per item in board order, the same form as the core renderer
// with ids off. A text that would read back as an id token gets one leading backslash.
function boardMarkdown(items) {
  return items
    .map(item => {
      const indent = isTopLevel(item) ? '' : '  '
      const box = item.checked ? '[x]' : '[ ]'
      const text = ESCAPED_HASH.test(item.text) ? `\\${item.text}` : item.text
      return `${indent}- ${box} ${text}\n`
    })
    .join('')
}

function pendingItem(op, pendingKey) {
  const parent = op.parent_id === undefined ? null : op.parent_id
  return { id: null, pendingKey, parent_id: parent, text: op.text, checked: false }
}

// A subtask goes after the last subtask of its parent. A top-level item goes last.
// An add under a parent that the board does not hold changes nothing.
function insertPending(items, entry) {
  if (isTopLevel(entry)) return [...items, entry]
  const parentAt = items.findIndex(item => item.id === entry.parent_id)
  if (parentAt < 0) return items
  let at = parentAt
  items.forEach((item, index) => {
    if (item.parent_id === entry.parent_id) at = index
  })
  return [...items.slice(0, at + 1), entry, ...items.slice(at + 1)]
}

// Returns a new board. Never mutates its input. An op it does not know leaves the board as it is.
// An add shows as a pending item with no id: pendingKey names it until the reply brings the real item.
function applyOp(board, op, pendingKey) {
  const items = boardItems(board)
  if (op.op === 'add') {
    return { ...board, items: insertPending(items, pendingItem(op, pendingKey)) }
  }
  if (op.op === 'remove') {
    const kept = items.filter(item => item.id !== op.item_id && item.parent_id !== op.item_id)
    return { ...board, items: kept }
  }
  if (op.op !== 'set_checked' && op.op !== 'set_text') return board
  const field = op.op === 'set_text' ? { text: op.text } : { checked: op.checked }
  if (!items.some(item => item.id === op.item_id)) return board
  return {
    ...board,
    items: items.map(item => (item.id === op.item_id ? { ...item, ...field } : item))
  }
}

function confirmText(count) {
  return `Delete this item and its ${count === 1 ? '1 subtask' : `${count} subtasks`}?`
}

// Returns a new board with every pending write applied in order. Never mutates its input.
function viewBoard(board, pendingEntries) {
  return pendingEntries.reduce((view, entry) => applyOp(view, entry.op, `pending-${entry.seq}`), board)
}

function hasItem(board, itemId) {
  return boardItems(board).some(item => item.id === itemId)
}

// 'ok', 'retry' (a stale check that may go once more), 'stale' or 'failed'.
function writeOutcome(reply, op, retried) {
  if (reply && reply.ok === true) return 'ok'
  const isStale = reply && reply.ok === false && reply.error === 'stale' && reply.board
  if (!isStale) return 'failed'
  const mayRetry = op.op === 'set_checked' && !retried && hasItem(reply.board, op.item_id)
  return mayRetry ? 'retry' : 'stale'
}

function boardPath(sid) {
  return `/board?session_id=${encodeURIComponent(sid)}`
}

function isMismatch(meta) {
  if (!meta || meta.ok !== true) return false
  return meta.backend_version !== PLUGIN_VERSION || meta.api_version !== API_VERSION
}

// The copy notice sentence in pieces: head, title, tail and the whole. Counts are numerals.
// The cap clause follows only when some items were cut.
function copyNoticeText({ copied, skipped, overflow, label }) {
  const cut = overflow > 0 ? ` ${overflow} not copied, the board holds ${BOARD_CAP} items.` : ''
  const head = `Copied ${copied} to `
  const tail = `. ${skipped} skipped, already on the board.${cut}`
  return { head, title: label, tail, full: `${head}${label}${tail}` }
}

// One message at a time: version mismatch, then the latest notice (write failed, stale or copied), then load failed.
function noticeText({ meta, notice, loadFailed }) {
  if (isMismatch(meta)) return MISMATCH_LINE
  const kind = notice ? notice.kind : null
  if (kind === 'failed') return WRITE_FAILED_NOTICE
  if (kind === 'stale') return STALE_NOTICE
  if (kind === 'copied') return copyNoticeText(notice.data).full
  return loadFailed ? LOAD_FAILED_NOTICE : null
}

// The copied notice that shows now, or null. A version mismatch hides it.
function copiedNotice({ meta, notice }) {
  if (isMismatch(meta) || !notice || notice.kind !== 'copied') return null
  return copyNoticeText(notice.data)
}

// The copied notice is one flex line of three pieces: head and tail never shrink, only the title ends with an ellipsis.
function Notice({ text, copied }) {
  if (!text) return null
  if (!copied) return jsx('div', { className: NOTICE_CLASS, style: NOTICE_STYLE, role: 'status', children: text })
  return jsxs('div', {
    className: NOTICE_CLASS,
    style: COPIED_NOTICE_STYLE,
    role: 'status',
    title: copied.full,
    children: [
      jsx('span', { className: 'shrink-0', children: copied.head }),
      jsx('span', { style: TRUNCATE_STYLE, children: copied.title }),
      jsx('span', { className: 'shrink-0', children: copied.tail })
    ]
  })
}

// Copy all open to the focused board. The label truncates; the full label is in the Tip and the aria-label.
function CopyAllButton({ label, disabled, onClick }) {
  return jsx(Tip, {
    label,
    children: jsx(Button, {
      variant: 'outline',
      size: 'sm',
      className: 'min-w-0',
      'aria-label': label,
      disabled,
      onClick,
      children: jsx('span', { style: TRUNCATE_STYLE, children: label })
    })
  })
}

// `copyAll` is { label, disabled, onClick } in the read-only view and null on the focused board.
function Header({ items, copyAll }) {
  return jsxs('div', {
    className: HEADER_ROW_CLASS,
    children: [
      copyAll === null ? null : jsx(CopyAllButton, copyAll),
      jsx(CopyButton, {
        appearance: 'icon',
        label: 'Copy as markdown',
        text: () => boardMarkdown(items),
        disabled: items.length === 0
      })
    ]
  })
}

// One board in the menu. The right block and the check slot never shrink; the name truncates.
function MenuRow({ rootId, counts, updatedAt, view, onSelect }) {
  const { titles, focusedRoot, shownRoot, nowMs } = view
  const sub = menuSubLine(rootId, focusedRoot, titles)
  const time = updatedLabel(updatedAt, nowMs)
  const current = rootId === shownRoot
  return jsxs(DropdownMenuItem, {
    onSelect,
    'aria-current': current ? true : undefined,
    children: [
      jsxs('span', {
        className: MENU_LEFT_CLASS,
        children: [
          jsx('span', { className: MENU_NAME_CLASS, style: TRUNCATE_STYLE, children: menuName(rootId, titles) }),
          sub === null ? null : jsx('span', { className: MENU_SUB_CLASS, style: TRUNCATE_STYLE, children: sub })
        ]
      }),
      jsxs('span', {
        className: MENU_RIGHT_CLASS,
        style: NOWRAP_STYLE,
        children: [
          counts.total === 0 ? null : jsx('span', { style: NOWRAP_STYLE, children: headerText(counts) }),
          time === null ? null : jsx('span', { style: NOWRAP_STYLE, children: time })
        ]
      }),
      jsx('span', { className: CARET_CLASS, children: current ? jsx(icons.Check, {}) : null })
    ]
  })
}

// The menu: the focused board, a hairline, then the others or one plain line that says why there are none.
function PickerMenu({ view, boards, failed, focusedCounts, onPick }) {
  const { focused, others } = orderBoards(boards, view.focusedRoot)
  const first = focused === null ? { open: focusedCounts.open, total: focusedCounts.total } : focused
  const tail = []
  if (failed) {
    tail.push(jsx(DropdownMenuItem, { disabled: true, children: LIST_FAILED }, 'failed'))
  } else if (boards !== null && others.length === 0) {
    tail.push(jsx(DropdownMenuItem, { disabled: true, children: NO_OTHER_BOARDS }, 'none'))
  } else if (boards !== null) {
    for (const board of others) {
      tail.push(
        jsx(
          MenuRow,
          {
            rootId: board.root_id,
            counts: { open: board.open, total: board.total },
            updatedAt: board.updated_at,
            view,
            onSelect: () => onPick(board.root_id)
          },
          board.root_id
        )
      )
    }
  }
  return jsxs(DropdownMenuContent, {
    align: 'start',
    style: MENU_STYLE,
    children: [
      jsx(
        MenuRow,
        {
          rootId: view.focusedRoot,
          counts: { open: first.open, total: first.total },
          updatedAt: focused === null ? null : focused.updated_at,
          view,
          onSelect: () => onPick(view.focusedRoot)
        },
        'focused'
      ),
      jsx(DropdownMenuSeparator, {}),
      ...tail
    ]
  })
}

// The first element of the pane: the shown board and its count, and the menu of every board.
function PickerRow({ view, counts, boards, failed, focusedCounts, triggerRef, onOpenChange, onPick }) {
  const label = boardLabel(view.shownRoot, view.titles)
  return jsx('div', {
    className: PICKER_ROW_CLASS,
    children: jsxs(DropdownMenu, {
      onOpenChange,
      children: [
        jsx(Tip, {
          label: PICKER_TIP,
          children: jsx(DropdownMenuTrigger, {
            asChild: true,
            children: jsxs(Button, {
              ref: triggerRef,
              variant: 'outline',
              size: 'sm',
              className: PICKER_BUTTON_CLASS,
              'aria-label': pickerAriaLabel(label, counts),
              children: [
                jsx('span', { className: PICKER_TITLE_CLASS, style: TRUNCATE_STYLE, children: label }),
                counts.total === 0
                  ? null
                  : jsx('span', { className: PICKER_COUNT_CLASS, style: NOWRAP_STYLE, children: headerText(counts) }),
                jsx(icons.ChevronDown, { className: CARET_CLASS })
              ]
            })
          })
        }),
        jsx(PickerMenu, { view, boards, failed, focusedCounts, onPick })
      ]
    })
  })
}

function ReadOnlyBanner({ focusedLabel, onBack }) {
  return jsxs('div', {
    className: BANNER_CLASS,
    children: [
      READ_ONLY_BANNER,
      jsx(Button, {
        variant: 'text',
        size: 'inline',
        className: 'underline',
        'aria-label': `Back to ${focusedLabel}`,
        onClick: onBack,
        children: BACK_LABEL
      })
    ]
  })
}

function Chevron({ hasChildren, collapsed, onToggle }) {
  if (!hasChildren) return null
  const label = collapsed ? 'Expand subtasks' : 'Collapse subtasks'
  const Icon = collapsed ? icons.ChevronRight : icons.ChevronDown
  return jsx('span', {
    className: HIT_CLASS,
    children: jsx(Tip, {
      label,
      children: jsx(Button, {
        variant: 'ghost',
        size: 'icon-xs',
        'aria-label': label,
        onClick: onToggle,
        children: jsx(Icon, {})
      })
    })
  })
}

function RowButton({ label, Icon, onClick }) {
  return jsx(Tip, {
    label,
    children: jsx(Button, {
      variant: 'ghost',
      size: 'icon-xs',
      className: ROW_BUTTON_CLASS,
      'aria-label': label,
      onClick,
      children: jsx(Icon, {})
    })
  })
}

// The text of a saved item shows as a clickable span, or as the one edit Input while it is edited.
function RowText({ item, textClass, actions }) {
  const { edit } = actions
  if (edit !== null && edit.id === item.id) {
    return jsx(AddLine, {
      className: EDIT_CLASS,
      value: edit.text,
      autoFocus: true,
      onChange: actions.onEditChange,
      onKeyDown: actions.onEditKey,
      onBlur: actions.onEditBlur,
      onFocus: caretToEnd
    })
  }
  return jsx('span', {
    className: textClass,
    style: item.checked ? DONE_STYLE : TEXT_STYLE,
    onClick: isPending(item) || actions.readOnly === true ? undefined : () => actions.onEdit(item),
    children: item.text
  })
}

function ItemRow({ item, subtasks, collapsed, onToggle, actions }) {
  const textClass = item.checked ? `${TEXT_CLASS} ${DONE_CLASS}` : TEXT_CLASS
  const top = isTopLevel(item)
  const pendingRow = isPending(item)
  const readOnly = actions.readOnly === true
  return jsxs('div', {
    className: top ? ROW_CLASS : SUBTASK_ROW_CLASS,
    'data-item-id': rowId(item),
    children: [
      jsx('span', {
        className: HIT_CLASS,
        // A press on the box keeps the focus where it is, so an open edit Input stays open.
        onMouseDown: event => event.preventDefault(),
        children: jsx(Checkbox, {
          className: CHECK_CLASS,
          checked: item.checked,
          disabled: pendingRow || readOnly,
          onCheckedChange: readOnly
            ? undefined
            : value => (pendingRow ? undefined : actions.onCheck(item, value)),
          'aria-label': item.text
        })
      }),
      jsx(RowText, { item, textClass, actions }),
      top ? jsx(Chevron, { hasChildren: subtasks.length > 0, collapsed, onToggle }) : null,
      top && subtasks.length > 0
        ? jsx('span', { className: COUNT_CLASS, children: subtaskCountText(subtasks) })
        : null,
      top && !pendingRow && !readOnly
        ? jsx(RowButton, {
            label: 'Add subtask',
            Icon: icons.Plus,
            onClick: () => actions.onAddSubtask(item.id)
          })
        : null,
      top && readOnly
        ? jsx(Tip, {
            label: actions.copyAria,
            children: jsx(Button, {
              variant: 'ghost',
              size: 'sm',
              className: ROW_COPY_CLASS,
              'aria-label': actions.copyAria,
              disabled: actions.copyBusy,
              onClick: () => actions.onCopy(item.id),
              children: COPY_LABEL
            })
          })
        : null,
      pendingRow || readOnly
        ? null
        : jsx(RowButton, {
            label: 'Delete item',
            Icon: icons.Trash2,
            onClick: () => actions.onDelete(item, subtasks)
          })
    ]
  })
}

// One top-level item: its row, one row per subtask, then its open subtask add line.
// `subtask` holds the AddLine props of that line ({ value, readOnly, onChange, onKeyDown, onBlur }), or null.
function ItemBlock({ group, collapsed, onToggle, actions, subtask }) {
  const { item, children } = group
  return jsxs('div', {
    'data-item-id': rowId(item),
    children: [
      jsx(ItemRow, {
        item,
        subtasks: children,
        collapsed,
        onToggle: () => onToggle(item.id),
        actions
      }),
      ...(collapsed
        ? []
        : children.map(child => jsx(ItemRow, { item: child, subtasks: [], actions }, itemKey(child)))),
      subtask !== null && !collapsed
        ? jsx(
            AddLine,
            { className: SUBTASK_LINE_CLASS, placeholder: SUBTASK_PLACEHOLDER, autoFocus: true, ...subtask },
            'subtask-line'
          )
        : null
    ]
  })
}

// One text line. It holds no state: the caller owns the text, the busy flag and the handlers.
function AddLine({
  className,
  placeholder,
  value,
  readOnly,
  autoFocus,
  inputRef,
  onChange,
  onKeyDown,
  onBlur,
  onFocus
}) {
  return jsx('div', {
    className,
    children: jsx(Input, {
      ref: inputRef,
      placeholder,
      value,
      readOnly,
      autoFocus,
      maxLength: MAX_TEXT_CHARS,
      size: 'sm',
      onChange: event => onChange(event.target.value),
      onKeyDown,
      onBlur,
      onFocus
    })
  })
}

// Puts the caret after the last character when an edit Input takes focus.
function caretToEnd(event) {
  const field = event.target
  field.setSelectionRange(field.value.length, field.value.length)
}

function DeleteConfirm({ confirm, onClose, onConfirm }) {
  return jsx(ConfirmDialog, {
    open: confirm !== null,
    title: CONFIRM_TITLE,
    description: confirm === null ? null : confirmText(confirm.count),
    confirmLabel: CONFIRM_LABEL,
    cancelLabel: CANCEL_LABEL,
    destructive: true,
    onClose,
    onConfirm
  })
}

function isEnter(event) {
  return event.key === 'Enter' && !(event.nativeEvent && event.nativeEvent.isComposing)
}

function Pane({ ctx }) {
  const sid = useValue(host.state.focusedStoredSessionId)
  const [meta, setMeta] = useState(null)
  // The last accepted board reply: { sid, rev, root_id, board }.
  const [server, setServer] = useState(null)
  // The writes that wait for a reply, in click order: { seq, sid, op }.
  const [pending, setPending] = useState([])
  // The one notice that shows: { kind: 'stale' | 'failed', seq }, or null.
  const [notice, setNotice] = useState(null)
  const [loadFailed, setLoadFailed] = useState(false)
  // The parents whose subtasks are hidden, keyed by item id. It lives here only and starts empty.
  const [collapsed, setCollapsed] = useState({})
  // The add line: its text and whether a write for it is in flight. addRef holds its Input element.
  const [addText, setAddText] = useState('')
  const [addBusy, setAddBusy] = useState(false)
  const addRef = useRef(null)
  // The picker trigger element, and a flag set by Back: the one case where the pane moves keyboard focus.
  const triggerRef = useRef(null)
  const focusAfterBack = useRef(false)
  // The open subtask add lines, keyed by parent id: { text, busy }.
  const [subLines, setSubLines] = useState({})
  // The one item under edit: { id, text, original }, or null. The ref copy lives in `current`.
  const [edit, setEdit] = useState(null)
  // The delete question for an item with subtasks: { id, count }, or null.
  const [confirm, setConfirm] = useState(null)
  // Hermes titles by board root id, the boards of the menu (null until the first reply) and whether that list failed.
  const [titles, setTitles] = useState({})
  const [boards, setBoards] = useState(null)
  const [boardsFailed, setBoardsFailed] = useState(false)
  // When the menu opened: the time labels are computed against it and nothing ticks.
  const [menuNow, setMenuNow] = useState(0)
  // The root id of the other board under view, its last reply, and its own collapse map (null view = focused board).
  const [picked, setPicked] = useState(null)
  const [pickedServer, setPickedServer] = useState(null)
  const [pickedCollapsed, setPickedCollapsed] = useState({})
  // True from a copy click until its outcome: every copy control is disabled meanwhile.
  const [copyBusy, setCopyBusy] = useState(false)
  const shown = server !== null && server.sid === (sid || null) ? server : null
  // The listener, the interval and the writes live longer than one render, so they read this ref.
  // revs holds the newest accepted rev of each session. queue chains the writes one after another.
  const current = useRef({
    sid: null,
    revs: {},
    rootRevs: {},
    focusedRoot: null,
    inFlight: 0,
    queue: Promise.resolve(),
    seq: 0,
    entrySeq: 0,
    visit: 0,
    kept: {},
    addBusy: false,
    copyBusy: false,
    subBusy: {},
    edit: null,
    board: null,
    picked: null,
    noticeCleanup: null
  })
  const focused = sid || null

  function take(asked, reply) {
    current.current.revs[asked] = reply.rev
    if (current.current.sid !== asked) return
    current.current.board = reply.board
    current.current.focusedRoot = reply.root_id
    const open = current.current.edit
    if (open !== null && !hasItem(reply.board, open.id)) {
      changeEdit(null)
      showNotice('stale')
    }
    setServer({ sid: asked, rev: reply.rev, root_id: reply.root_id, board: reply.board })
  }

  // The ref is the truth for handlers that run before the next render.
  function changeEdit(next) {
    current.current.edit = next
    setEdit(next)
  }

  // A reload reply never undoes a write: it is dropped while a write is in flight, and when its rev is
  // lower than the newest accepted rev of the session. A dropped reply changes no state.
  function reload() {
    const asked = current.current.sid
    if (!asked) return Promise.resolve()
    return ctx
      .rest(boardPath(asked))
      .then(body => {
        if (!body || body.ok !== true) return
        const state = current.current
        if (state.sid !== asked || state.inFlight > 0) return
        if (body.rev < (state.revs[asked] ?? 0)) return
        take(asked, body)
        setLoadFailed(false)
      })
      .catch(() => {
        if (current.current.sid === asked) setLoadFailed(true)
      })
  }

  // The root id of the board under view: the picked one, else the focused one once its first reply came.
  function shownRoot() {
    const state = current.current
    return state.picked ?? state.focusedRoot
  }

  // The same rules as reload for the picked board. Its revs are keyed by root id and never mix with the focused ones.
  function reloadPicked() {
    const asked = current.current.picked
    if (asked === null) return Promise.resolve()
    return ctx
      .rest(boardPath(asked))
      .then(body => {
        if (!body || body.ok !== true) throw new Error('bad reply')
        const state = current.current
        if (state.picked !== asked) return
        if (body.rev < (state.rootRevs[asked] ?? 0)) return
        state.rootRevs[asked] = body.rev
        setPickedServer(body)
        setLoadFailed(false)
      })
      .catch(() => {
        if (current.current.picked === asked) setLoadFailed(true)
      })
  }

  function reloadShown() {
    return current.current.picked === null ? reload() : reloadPicked()
  }

  // Titles come from Hermes. A failed or odd reply keeps the last good titles and shows nothing.
  function loadTitles() {
    try {
      return Promise.resolve(host.request('session.list', { limit: SESSION_LIST_LIMIT }))
        .then(reply => {
          if (reply && Array.isArray(reply.sessions)) setTitles(titleMap(reply.sessions))
        })
        .catch(() => undefined)
    } catch {
      return Promise.resolve()
    }
  }

  function loadBoards() {
    return ctx
      .rest('/boards')
      .then(body => {
        const good = body && body.ok === true && Array.isArray(body.boards)
        if (good) setBoards(body.boards)
        setBoardsFailed(!good)
      })
      .catch(() => setBoardsFailed(true))
  }

  // The menu refreshes when it opens, never on the poll.
  function onMenuOpenChange(open) {
    if (!open) return
    setMenuNow(Date.now())
    loadBoards()
    loadTitles()
  }

  function showNotice(kind, data) {
    const state = current.current
    state.seq += 1
    const mine = state.seq
    if (typeof state.noticeCleanup === 'function') state.noticeCleanup()
    setNotice({ kind, seq: mine, data })
    state.noticeCleanup = ctx.setTimeout(() => {
      if (current.current.seq === mine) setNotice(null)
    }, NOTICE_MS)
  }

  // Posts the op on the newest accepted rev. A stale check shows the returned board and goes once more.
  async function postOp(asked, op) {
    let retried = false
    for (;;) {
      const reply = await ctx.rest('/board/edit', {
        method: 'POST',
        body: { session_id: asked, ops: [op], base_rev: current.current.revs[asked] ?? 0 }
      })
      const outcome = writeOutcome(reply, op, retried)
      if (outcome === 'failed') return 'failed'
      take(asked, reply)
      if (outcome === 'ok') return 'ok'
      showNotice('stale')
      if (outcome === 'stale') return 'stale'
      retried = true
    }
  }

  async function runWrite(asked, entry, onOutcome) {
    current.current.inFlight += 1
    let outcome = 'failed'
    try {
      outcome = await postOp(asked, entry.op)
    } catch {
      outcome = 'failed'
    } finally {
      current.current.inFlight -= 1
      setPending(prev => prev.filter(item => item !== entry))
    }
    // onOutcome runs even when the notice throws, so a busy flag never stays set.
    try {
      if (outcome === 'failed') {
        reload()
        showNotice('failed')
      }
    } finally {
      if (onOutcome) onOutcome(outcome)
    }
  }

  // Copies into the focused board `asked` from the board `fromRoot`. One request, never retried.
  // The rev is read when the copy runs, so a write queued before it has moved the rev already.
  async function runCopy(asked, fromRoot, itemIds, label) {
    const state = current.current
    state.inFlight += 1
    let outcome = 'failed'
    let reply = null
    try {
      const body = { session_id: asked, from_session_id: fromRoot, base_rev: state.revs[asked] ?? 0 }
      if (itemIds !== null) body.item_ids = itemIds
      reply = await ctx.rest('/board/copy', { method: 'POST', body })
      const isStale = reply && reply.ok === false && reply.error === 'stale' && reply.board
      if (reply && reply.ok === true) outcome = 'ok'
      else if (isStale) outcome = 'stale'
      if (outcome !== 'failed') take(asked, reply)
    } catch {
      outcome = 'failed'
    } finally {
      state.inFlight -= 1
    }
    try {
      if (outcome === 'ok') {
        const { copied = 0, skipped = 0, overflow = 0 } = reply
        if (state.sid === asked) showNotice('copied', { copied, skipped, overflow, label })
      } else if (outcome === 'stale') {
        reloadPicked()
        showNotice('stale')
      } else {
        reload()
        showNotice('failed')
      }
    } finally {
      state.copyBusy = false
      setCopyBusy(false)
    }
  }

  // Starts a copy and returns nothing. `itemIds` null copies every open item. The session and the root
  // are read now, at click time, and the copy waits in the write queue behind earlier writes.
  function copyItems(itemIds, label) {
    const state = current.current
    const asked = state.sid
    const fromRoot = state.picked
    if (!asked || fromRoot === null || state.copyBusy) return
    state.copyBusy = true
    setCopyBusy(true)
    state.queue = state.queue.then(() => runCopy(asked, fromRoot, itemIds, label)).catch(() => undefined)
  }

  useEffect(() => {
    let live = true
    ctx
      .rest('/meta')
      .then(body => live && setMeta(body))
      .catch(() => live && setMeta(null))
    return () => {
      live = false
    }
  }, [])

  // A focus change starts a new visit. A write that settles in a later visit changes no line state.
  // The render never writes the ref: a render React drops must not move the session of a write.
  // A rev only grows, so the revs of other sessions stay and reload drops any lower reply.
  useEffect(() => {
    current.current.sid = focused
    current.current.board = null
    current.current.picked = null
    current.current.focusedRoot = null
    setPicked(null)
    setPickedServer(null)
    setPickedCollapsed({})
    current.current.visit += 1
    current.current.addBusy = false
    current.current.subBusy = {}
    setCollapsed({})
    setAddText('')
    setAddBusy(false)
    setSubLines({})
    changeEdit(null)
    setConfirm(null)
    setLoadFailed(false)
    if (!sid) {
      setServer(null)
      return undefined
    }
    loadTitles()
    reload()
    return ctx.setInterval(reloadShown, POLL_MS)
  }, [sid])

  // After Back the picker trigger takes focus, so a keyboard user stays where the view change began.
  // The flag is set only by Back, so a first render, a pick or a focus change never moves focus.
  useEffect(() => {
    if (picked !== null || !focusAfterBack.current) return
    focusAfterBack.current = false
    const trigger = triggerRef.current
    if (trigger && typeof trigger.focus === 'function') trigger.focus()
  }, [picked])

  // An event for another board changes nothing here. A missing payload or root reloads the shown board.
  useEffect(
    () =>
      ctx.onEvent(EVENT_TYPE, event => {
        const root = event?.payload?.root_id
        const shown = shownRoot()
        if (!root || shown === null || root === shown) reloadShown()
      }),
    []
  )

  // Starts the write and returns nothing: a caller must never wait on the write.
  // onOutcome runs once with 'ok', 'stale' or 'failed' after the write settles.
  // `asked` names the session the caller started on, and defaults to the focused one.
  function sendOp(op, onOutcome, asked = current.current.sid) {
    if (!asked) return
    current.current.entrySeq += 1
    const entry = { seq: current.current.entrySeq, sid: asked, op }
    setPending(prev => [...prev, entry])
    // A throw ends this write only: the catch keeps the queue alive for the next one.
    current.current.queue = current.current.queue
      .then(() => runWrite(asked, entry, onOutcome))
      .catch(() => undefined)
  }

  // Enter in the add line. The ref guards a second Enter that arrives before the next render.
  function submitAdd() {
    const state = current.current
    const text = addText.trim()
    if (state.addBusy || text === '') return
    const visit = state.visit
    state.addBusy = true
    setAddBusy(true)
    sendOp({ op: 'add', text }, outcome => {
      if (state.visit !== visit) return
      state.addBusy = false
      setAddBusy(false)
      if (outcome !== 'ok') return
      setAddText('')
      const input = addRef.current
      if (input && typeof input.scrollIntoView === 'function') input.scrollIntoView({ block: 'nearest' })
    })
  }

  // Escape clears the line, except while its write is in flight: a failed write puts the text back.
  function onAddKeyDown(event) {
    if (isEnter(event)) submitAdd()
    else if (event.key === 'Escape' && !current.current.addBusy) setAddText('')
  }

  function patchSubLine(parentId, patch) {
    setSubLines(prev =>
      prev[parentId] ? { ...prev, [parentId]: { ...prev[parentId], ...patch } } : prev
    )
  }

  function closeSubLine(parentId) {
    setSubLines(({ [parentId]: closed, ...rest }) => rest)
  }

  // The plus click: lines without text close, this parent gets an empty line and shows its subtasks.
  function openSubLine(parentId) {
    setSubLines(prev => {
      const kept = Object.fromEntries(Object.entries(prev).filter(([, line]) => line.text !== ''))
      return kept[parentId] ? kept : { ...kept, [parentId]: { text: '', busy: false } }
    })
    setCollapsed(prev => ({ ...prev, [parentId]: false }))
  }

  function submitSubtask(parentId, line) {
    const state = current.current
    const text = line.text.trim()
    if (state.subBusy[parentId] || text === '') return
    const visit = state.visit
    state.subBusy[parentId] = true
    patchSubLine(parentId, { busy: true })
    sendOp({ op: 'add', text, parent_id: parentId }, outcome => {
      if (state.visit !== visit) return
      delete state.subBusy[parentId]
      patchSubLine(parentId, outcome === 'ok' ? { text: '', busy: false } : { busy: false })
    })
  }

  // Escape closes the line, except while its write is in flight. Blur closes it only when it holds no text.
  function subtaskHandlers(parentId, line) {
    return {
      value: line.text,
      readOnly: line.busy,
      onChange: value => patchSubLine(parentId, { text: value }),
      onKeyDown: event => {
        if (isEnter(event)) submitSubtask(parentId, line)
        else if (event.key === 'Escape' && !line.busy) closeSubLine(parentId)
      },
      onBlur: () => {
        if (line.text === '' && !line.busy) closeSubLine(parentId)
      }
    }
  }

  function startEdit(item) {
    const open = current.current.edit
    if (open !== null && open.id === item.id) return
    saveEdit()
    const state = current.current
    const key = `${state.sid}:${item.id}`
    const text = state.kept[key] ?? item.text
    delete state.kept[key]
    changeEdit({ sid: state.sid, id: item.id, text, original: item.text })
  }

  // Reads the edit from the ref, so an Enter followed by a blur sends one write.
  // Item ids are per board, so an edit never writes or reopens on another session than its own.
  // A failed write reopens the edit, or else leaves the text in `kept` for the next edit of that item.
  function saveEdit() {
    const state = current.current
    const open = state.edit
    if (open === null) return
    changeEdit(null)
    const text = open.text.trim()
    if (text === '' || text === open.original || open.sid !== state.sid) return
    sendOp({ op: 'set_text', item_id: open.id, text }, outcome => {
      if (outcome === 'ok') return
      const sameBoard = state.sid === open.sid && hasItem(state.board, open.id)
      if (sameBoard && state.edit === null) changeEdit({ ...open, text })
      else state.kept[`${open.sid}:${open.id}`] = text
    }, open.sid)
  }

  const editHandlers = {
    onEditChange: value => {
      const open = current.current.edit
      if (open !== null) changeEdit({ ...open, text: value })
    },
    onEditKey: event => {
      if (isEnter(event)) saveEdit()
      else if (event.key === 'Escape') changeEdit(null)
    },
    onEditBlur: () => saveEdit()
  }

  // An item with no subtasks goes at once. One with subtasks asks first, naming the count.
  function onDelete(item, children) {
    if (children.length === 0) sendOp({ op: 'remove', item_id: item.id })
    else setConfirm({ id: item.id, count: children.length })
  }

  function confirmDelete() {
    if (confirm === null) return
    setConfirm(null)
    sendOp({ op: 'remove', item_id: confirm.id })
  }

  // Leaves the board under view and reloads the focused one at once. The focused board's lines and pending writes stay in state.
  function back() {
    focusAfterBack.current = current.current.picked !== null
    current.current.picked = null
    setPicked(null)
    setPickedServer(null)
    reload()
  }

  // The focused board, or another one under view. Picking the focused or the shown board returns to the focused one.
  function pick(rootId, focusedRoot) {
    const state = current.current
    if (rootId === focusedRoot || rootId === state.picked) {
      back()
      return
    }
    saveEdit()
    state.picked = rootId
    setPicked(rootId)
    setPickedServer(null)
    setPickedCollapsed({})
    // The picked board loads after a write that saveEdit just queued.
    state.queue.then(reloadPicked)
  }

  const onCheck = (item, value) => sendOp({ op: 'set_checked', item_id: item.id, checked: value === true })
  const onToggle = itemId => setCollapsed(prev => ({ ...prev, [itemId]: !prev[itemId] }))
  const actions = { edit, onCheck, onAddSubtask: openSubLine, onEdit: startEdit, onDelete, ...editHandlers }
  const focusedEntries = pending.filter(entry => entry.sid === focused)
  const board = shown === null ? null : viewBoard(shown.board, focusedEntries)
  const items = boardItems(board)
  const noticeLine = jsx(Notice, {
    text: noticeText({ meta, notice, loadFailed }),
    copied: copiedNotice({ meta, notice })
  })
  if (focused === null) {
    return jsxs('div', {
      className: PANE_CLASS,
      children: [noticeLine, jsx(EmptyState, { title: NO_CHAT_TITLE })]
    })
  }
  const focusedRoot = shown === null ? focused : shown.root_id
  const focusedLabel = boardLabel(focusedRoot, titles)
  const copyAllLabel = `${COPY_ALL_PREFIX}${focusedLabel}`
  const readOnlyActions = {
    readOnly: true,
    edit: null,
    copyAria: `${COPY_ROW_ARIA}${focusedLabel}`,
    copyBusy,
    onCopy: itemId => copyItems([itemId], focusedLabel)
  }
  const viewing = picked !== null
  const shownItems = viewing ? boardItems(pickedServer === null ? null : pickedServer.board) : items
  const view = {
    titles,
    focusedRoot,
    shownRoot: viewing ? picked : focusedRoot,
    nowMs: menuNow
  }
  const isEmpty = viewing ? pickedServer !== null && shownItems.length === 0 : shown !== null && items.length === 0
  const emptyState = viewing
    ? jsx(EmptyState, { title: READ_ONLY_EMPTY_TITLE, description: READ_ONLY_EMPTY_HINT }, 'empty')
    : jsx(EmptyState, { title: EMPTY_TITLE, description: EMPTY_HINT }, 'empty')
  const collapseMap = viewing ? pickedCollapsed : collapsed
  const onToggleShown = viewing
    ? itemId => setPickedCollapsed(prev => ({ ...prev, [itemId]: !prev[itemId] }))
    : onToggle
  return jsxs('div', {
    className: PANE_CLASS,
    children: [
      jsx(PickerRow, {
        view,
        counts: openCounts(shownItems),
        boards,
        failed: boardsFailed,
        focusedCounts: openCounts(items),
        triggerRef,
        onOpenChange: onMenuOpenChange,
        onPick: rootId => pick(rootId, focusedRoot)
      }),
      viewing
        ? jsx(ReadOnlyBanner, { focusedLabel, onBack: back })
        : null,
      jsx(Header, {
        items: shownItems,
        copyAll: viewing
          ? {
              label: copyAllLabel,
              disabled: copyBusy || openCounts(shownItems).open === 0,
              onClick: () => copyItems(null, focusedLabel)
            }
          : null
      }),
      noticeLine,
      jsx(ScrollArea, {
        className: LIST_CLASS,
        children: jsx('div', {
          className: LIST_BODY_CLASS,
          children: [
            isEmpty
              ? emptyState
              : buildTree(shownItems).map(group =>
                  jsx(
                    ItemBlock,
                    {
                      group,
                      collapsed: collapseMap[group.item.id] === true,
                      onToggle: onToggleShown,
                      actions: viewing ? readOnlyActions : actions,
                      subtask:
                        !viewing && subLines[group.item.id]
                          ? subtaskHandlers(group.item.id, subLines[group.item.id])
                          : null
                    },
                    itemKey(group.item)
                  )
                ),
            viewing
              ? null
              : jsx(AddLine, {
                  className: ADD_LINE_CLASS,
                  placeholder: ADD_PLACEHOLDER,
                  value: addText,
                  readOnly: addBusy,
                  inputRef: addRef,
                  onChange: setAddText,
                  onKeyDown: onAddKeyDown
                }, 'add')
          ]
        })
      }),
      jsx(DeleteConfirm, { confirm, onClose: () => setConfirm(null), onConfirm: confirmDelete })
    ]
  })
}

// Bring the pane on screen: un-hide it, open its collapsed zone and front its tab.
// A Desktop without host.revealPane does nothing here.
function showPane() {
  if (typeof host.revealPane === 'function') host.revealPane(PANE_ID)
}

export default {
  id: PLUGIN_ID,
  name: 'Session tasks',
  register(ctx) {
    ctx.register({
      id: PANE_KEY,
      area: 'panes',
      title: 'Session tasks',
      data: { placement: 'right', dock: { pane: 'workspace', pos: 'right' }, width: '320px' },
      render: () => jsx(Pane, { ctx })
    })
    ctx.register({
      id: 'show',
      area: 'statusBar.right',
      order: SHOW_ORDER,
      data: {
        id: `${PANE_ID}-show`,
        icon: jsx(Codicon, { name: SHOW_ICON, size: '0.75rem' }),
        label: SHOW_LABEL,
        title: SHOW_TITLE,
        toggleLabel: SHOW_TOGGLE_LABEL,
        variant: 'action',
        onSelect: showPane
      }
    })
    ctx.register({
      id: 'show-command',
      area: PALETTE_AREA,
      data: {
        id: `${PLUGIN_ID}.show`,
        label: SHOW_COMMAND,
        keywords: ['tasks', 'board', 'session', 'checklist'],
        run: showPane
      }
    })
  }
}

export {
  PANE_ID, SHOW_COMMAND, SHOW_LABEL, SHOW_TITLE, SHOW_TOGGLE_LABEL, showPane,
  API_VERSION, EVENT_TYPE, PLUGIN_ID, PLUGIN_VERSION, LOAD_FAILED_NOTICE, NOTICE_MS, POLL_MS,
  STALE_NOTICE, WRITE_FAILED_NOTICE, ADD_PLACEHOLDER, MAX_TEXT_CHARS, SUBTASK_PLACEHOLDER,
  PICKER_TIP, UNTITLED, NO_OTHER_BOARDS, LIST_FAILED, READ_ONLY_BANNER, SESSION_LIST_LIMIT,
  applyOp, boardItems, boardLabel, boardMarkdown, boardPath, buildTree, copyNoticeText, headerText, isMismatch,
  isTopLevel, menuName, menuSubLine, noticeText, openCounts, orderBoards, pickerAriaLabel,
  shortId, subtaskCountText, titleMap, updatedLabel, viewBoard, writeOutcome
}
