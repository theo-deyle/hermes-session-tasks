/**
 * Session tasks pane for hermes-session-tasks. Plain ESM, loaded uncompiled: UI is jsx() calls.
 * Only three imports resolve here: the plugin SDK, react and the jsx runtime.
 * It shows the focused session's board as checkbox rows and sends Theo's edits through the plugin routes.
 * Only Pane calls React hooks. Every other component is a plain function of its props.
 */

import {
  Button,
  Checkbox,
  ConfirmDialog,
  CopyButton,
  EmptyState,
  Input,
  ScrollArea,
  Tip,
  host,
  icons,
  useValue
} from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const PLUGIN_ID = 'hermes-session-tasks'
const PLUGIN_VERSION = '0.1.0'
const API_VERSION = 1
const POLL_MS = 6000
const NOTICE_MS = 4000
const EVENT_TYPE = 'plugin.hermes-session-tasks.board.updated'
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
const HEADER_CLASS = 'text-sm font-medium text-(--ui-text-secondary)'
const HEADER_ROW_CLASS =
  'flex items-center justify-between gap-2 border-b border-(--ui-stroke-secondary) p-2'
const NOTICE_CLASS = 'px-2 pt-2 text-xs text-(--ui-text-secondary)'
const ROW_CLASS = 'group flex min-h-8 items-start gap-1 py-1'
const SUBTASK_ROW_CLASS = 'group flex min-h-8 items-start gap-1 py-1 pl-6'
const CHEVRON_COL_CLASS = 'flex size-6 shrink-0 items-center justify-center'
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
  if (meta === null || meta.ok !== true) return false
  return meta.backend_version !== PLUGIN_VERSION || meta.api_version !== API_VERSION
}

// One message at a time, in the order: version mismatch, write failed, stale, load failed.
function noticeText({ meta, notice, loadFailed }) {
  if (isMismatch(meta)) return MISMATCH_LINE
  const kind = notice ? notice.kind : null
  if (kind === 'failed') return WRITE_FAILED_NOTICE
  if (kind === 'stale') return STALE_NOTICE
  return loadFailed ? LOAD_FAILED_NOTICE : null
}

function Notice({ text }) {
  if (!text) return null
  return jsx('div', { className: NOTICE_CLASS, style: NOTICE_STYLE, children: text })
}

function Header({ counts, items }) {
  return jsxs('div', {
    className: HEADER_ROW_CLASS,
    children: [
      jsx('span', { className: HEADER_CLASS, children: counts.total === 0 ? null : headerText(counts) }),
      jsx(CopyButton, {
        appearance: 'icon',
        label: 'Copy as markdown',
        text: () => boardMarkdown(items),
        disabled: items.length === 0
      })
    ]
  })
}

function Chevron({ hasChildren, collapsed, onToggle }) {
  if (!hasChildren) return null
  const label = collapsed ? 'Expand subtasks' : 'Collapse subtasks'
  const Icon = collapsed ? icons.ChevronRight : icons.ChevronDown
  return jsx('span', {
    className: CHEVRON_COL_CLASS,
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
    onClick: isPending(item) ? undefined : () => actions.onEdit(item),
    children: item.text
  })
}

function ItemRow({ item, subtasks, collapsed, onToggle, actions }) {
  const textClass = item.checked ? `${TEXT_CLASS} ${DONE_CLASS}` : TEXT_CLASS
  const top = isTopLevel(item)
  const pendingRow = isPending(item)
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
          disabled: pendingRow,
          onCheckedChange: value => (pendingRow ? undefined : actions.onCheck(item, value)),
          'aria-label': item.text
        })
      }),
      jsx(RowText, { item, textClass, actions }),
      top ? jsx(Chevron, { hasChildren: subtasks.length > 0, collapsed, onToggle }) : null,
      top && subtasks.length > 0
        ? jsx('span', { className: COUNT_CLASS, children: subtaskCountText(subtasks) })
        : null,
      top && !pendingRow
        ? jsx(RowButton, {
            label: 'Add subtask',
            Icon: icons.Plus,
            onClick: () => actions.onAddSubtask(item.id)
          })
        : null,
      pendingRow
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
  // The open subtask add lines, keyed by parent id: { text, busy }.
  const [subLines, setSubLines] = useState({})
  // The one item under edit: { id, text, original }, or null. The ref copy lives in `current`.
  const [edit, setEdit] = useState(null)
  // The delete question for an item with subtasks: { id, count }, or null.
  const [confirm, setConfirm] = useState(null)
  const shown = server !== null && server.sid === (sid || null) ? server : null
  // The listener, the interval and the writes live longer than one render, so they read this ref.
  // revs holds the newest accepted rev of each session. queue chains the writes one after another.
  const current = useRef({
    sid: null,
    revs: {},
    inFlight: 0,
    queue: Promise.resolve(),
    seq: 0,
    entrySeq: 0,
    addBusy: false,
    subBusy: {},
    edit: null,
    board: null,
    noticeCleanup: null
  })
  const focused = sid || null
  if (current.current.sid !== focused) {
    current.current.sid = focused
    delete current.current.revs[focused]
    current.current.board = null
  }

  function take(asked, reply) {
    current.current.revs[asked] = reply.rev
    if (current.current.sid !== asked) return
    current.current.board = reply.board
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

  function showNotice(kind) {
    const state = current.current
    state.seq += 1
    const mine = state.seq
    if (typeof state.noticeCleanup === 'function') state.noticeCleanup()
    setNotice({ kind, seq: mine })
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
    if (outcome === 'failed') {
      showNotice('failed')
      reload()
    }
    if (onOutcome) onOutcome(outcome)
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

  useEffect(() => {
    setCollapsed({})
    setAddText('')
    setAddBusy(false)
    setSubLines({})
    changeEdit(null)
    setConfirm(null)
    if (!sid) {
      setServer(null)
      return undefined
    }
    reload()
    return ctx.setInterval(reload, POLL_MS)
  }, [sid])

  useEffect(() => ctx.onEvent(EVENT_TYPE, () => reload()), [])

  // Starts the write and returns nothing: a caller must never wait on the write.
  // onOutcome runs once with 'ok', 'stale' or 'failed' after the write settles.
  function sendOp(op, onOutcome) {
    const asked = current.current.sid
    if (!asked) return
    current.current.entrySeq += 1
    const entry = { seq: current.current.entrySeq, sid: asked, op }
    setPending(prev => [...prev, entry])
    current.current.queue = current.current.queue.then(() => runWrite(asked, entry, onOutcome))
  }

  // Enter in the add line. The ref guards a second Enter that arrives before the next render.
  function submitAdd() {
    const state = current.current
    const text = addText.trim()
    if (state.addBusy || text === '') return
    const asked = state.sid
    state.addBusy = true
    setAddBusy(true)
    sendOp({ op: 'add', text }, outcome => {
      state.addBusy = false
      setAddBusy(false)
      if (outcome !== 'ok' || state.sid !== asked) return
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
    setSubLines(prev =>
      Object.fromEntries(Object.entries(prev).filter(([key]) => key !== String(parentId)))
    )
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
    const asked = state.sid
    state.subBusy[parentId] = true
    patchSubLine(parentId, { busy: true })
    sendOp({ op: 'add', text, parent_id: parentId }, outcome => {
      delete state.subBusy[parentId]
      const cleared = outcome === 'ok' && state.sid === asked
      patchSubLine(parentId, cleared ? { text: '', busy: false } : { busy: false })
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
    changeEdit({ id: item.id, text: item.text, original: item.text })
  }

  // Reads the edit from the ref, so an Enter followed by a blur sends one write.
  // A stale or failed write puts the typed text back when the item is still on the board.
  function saveEdit() {
    const state = current.current
    const open = state.edit
    if (open === null) return
    changeEdit(null)
    const text = open.text.trim()
    if (text === '' || text === open.original) return
    sendOp({ op: 'set_text', item_id: open.id, text }, outcome => {
      if (outcome === 'ok' || state.edit !== null || !hasItem(state.board, open.id)) return
      changeEdit({ ...open, text })
    })
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

  function onCheck(item, value) {
    sendOp({ op: 'set_checked', item_id: item.id, checked: value === true })
  }

  function onToggle(itemId) {
    setCollapsed(prev => ({ ...prev, [itemId]: !prev[itemId] }))
  }

  const actions = { edit, onCheck, onAddSubtask: openSubLine, onEdit: startEdit, onDelete, ...editHandlers }
  const focusedEntries = pending.filter(entry => entry.sid === focused)
  const board = shown === null ? null : viewBoard(shown.board, focusedEntries)
  const items = boardItems(board)
  if (focused === null) {
    return jsxs('div', {
      className: PANE_CLASS,
      children: [
        jsx(Notice, { text: noticeText({ meta, notice, loadFailed }) }),
        jsx(EmptyState, { title: NO_CHAT_TITLE })
      ]
    })
  }
  const isEmpty = shown !== null && items.length === 0
  return jsxs('div', {
    className: PANE_CLASS,
    children: [
      jsx(Header, { counts: openCounts(items), items }),
      jsx(Notice, { text: noticeText({ meta, notice, loadFailed }) }),
      jsx(ScrollArea, {
        className: LIST_CLASS,
        children: jsx('div', {
          className: LIST_BODY_CLASS,
          children: [
            isEmpty
              ? jsx(EmptyState, { title: EMPTY_TITLE, description: EMPTY_HINT }, 'empty')
              : buildTree(items).map(group =>
                  jsx(
                    ItemBlock,
                    {
                      group,
                      collapsed: collapsed[group.item.id] === true,
                      onToggle,
                      actions,
                      subtask: subLines[group.item.id]
                        ? subtaskHandlers(group.item.id, subLines[group.item.id])
                        : null
                    },
                    itemKey(group.item)
                  )
                ),
            jsx(AddLine, {
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

export default {
  id: PLUGIN_ID,
  name: 'Session tasks',
  register(ctx) {
    ctx.register({
      id: 'pane',
      area: 'panes',
      title: 'Session tasks',
      data: { placement: 'right', dock: { pane: 'workspace', pos: 'right' }, width: '320px' },
      render: () => jsx(Pane, { ctx })
    })
  }
}

export {
  API_VERSION, EVENT_TYPE, PLUGIN_ID, PLUGIN_VERSION, LOAD_FAILED_NOTICE, NOTICE_MS, POLL_MS,
  STALE_NOTICE, WRITE_FAILED_NOTICE, ADD_PLACEHOLDER, MAX_TEXT_CHARS, SUBTASK_PLACEHOLDER,
  applyOp, boardItems, boardMarkdown, boardPath, buildTree, headerText, isMismatch, isTopLevel,
  noticeText, openCounts, subtaskCountText, viewBoard, writeOutcome
}
