/**
 * Session tasks pane for hermes-session-tasks. Plain ESM, loaded uncompiled: UI is jsx() calls.
 * Only three imports resolve here: the plugin SDK, react and the jsx runtime.
 * It shows the focused session's board as checkbox rows and sends Theo's edits through the plugin routes.
 * Only Pane calls React hooks. Every other component is a plain function of its props.
 */

import { Button, Checkbox, CopyButton, ScrollArea, Tip, host, icons, useValue } from '@hermes/plugin-sdk'
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
const HEADER_CLASS = 'text-sm font-medium text-(--ui-text-secondary)'
const HEADER_ROW_CLASS =
  'flex items-center justify-between gap-2 border-b border-(--ui-stroke-secondary) p-2'
const NOTICE_CLASS = 'px-2 pt-2 text-xs text-(--ui-text-secondary)'
const ROW_CLASS = 'flex min-h-8 items-start gap-1 py-1'
const SUBTASK_ROW_CLASS = 'flex min-h-8 items-start gap-1 py-1 pl-6'
const CHEVRON_COL_CLASS = 'flex size-6 shrink-0 items-center justify-center'
const COUNT_CLASS = 'shrink-0 py-1 text-xs text-(--ui-text-secondary)'
const LIST_CLASS = 'min-h-0 flex-1'
const LIST_BODY_CLASS = 'flex flex-col p-2'
const ESCAPED_HASH = /^\\*#[0-9]+(?:\s|$)/
const HIT_CLASS = 'flex size-6 shrink-0 items-center justify-center'
const TEXT_CLASS = 'min-w-0 flex-1 py-1 text-xs'
const DONE_CLASS = 'text-(--ui-text-secondary)'
const TEXT_STYLE = { overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }
const DONE_STYLE = { ...TEXT_STYLE, textDecoration: 'line-through' }
const NOTICE_STYLE = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }

function isTopLevel(item) {
  return item.parent_id === null || item.parent_id === undefined
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

// Returns a new board. Never mutates its input. An op it does not know leaves the board as it is.
function applyOp(board, op) {
  if (op.op !== 'set_checked') return board
  const items = boardItems(board)
  if (!items.some(item => item.id === op.item_id)) return board
  return {
    ...board,
    items: items.map(item => (item.id === op.item_id ? { ...item, checked: op.checked } : item))
  }
}

// Returns a new board with every pending op applied in order. Never mutates its input.
function viewBoard(board, pendingOps) {
  return pendingOps.reduce(applyOp, board)
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
  if (!hasChildren) return jsx('span', { className: CHEVRON_COL_CLASS })
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

function ItemRow({ item, subtasks, collapsed, onToggle, onCheck }) {
  const textClass = item.checked ? `${TEXT_CLASS} ${DONE_CLASS}` : TEXT_CLASS
  const top = isTopLevel(item)
  return jsxs('div', {
    className: top ? ROW_CLASS : SUBTASK_ROW_CLASS,
    'data-item-id': String(item.id),
    children: [
      top ? jsx(Chevron, { hasChildren: subtasks.length > 0, collapsed, onToggle }) : null,
      jsx('span', {
        className: HIT_CLASS,
        children: jsx(Checkbox, {
          checked: item.checked,
          onCheckedChange: value => onCheck(item, value),
          'aria-label': item.text
        })
      }),
      jsx('span', {
        className: textClass,
        style: item.checked ? DONE_STYLE : TEXT_STYLE,
        children: item.text
      }),
      top && subtasks.length > 0
        ? jsx('span', { className: COUNT_CLASS, children: subtaskCountText(subtasks) })
        : null
    ]
  })
}

// One top-level item: its row, then one row per subtask. Plan 04-06 adds the subtask add line here.
function ItemBlock({ group, collapsed, onToggle, onCheck }) {
  const { item, children } = group
  return jsxs('div', {
    'data-item-id': String(item.id),
    children: [
      jsx(ItemRow, { item, subtasks: children, collapsed, onToggle: () => onToggle(item.id), onCheck }),
      ...(collapsed
        ? []
        : children.map(child => jsx(ItemRow, { item: child, subtasks: [], onCheck }, child.id)))
    ]
  })
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
    noticeCleanup: null
  })
  const focused = sid || null
  if (current.current.sid !== focused) {
    current.current.sid = focused
    delete current.current.revs[focused]
  }

  function take(asked, reply) {
    current.current.revs[asked] = reply.rev
    if (current.current.sid !== asked) return
    setServer({ sid: asked, rev: reply.rev, root_id: reply.root_id, board: reply.board })
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

  function onCheck(item, value) {
    sendOp({ op: 'set_checked', item_id: item.id, checked: value === true })
  }

  function onToggle(itemId) {
    setCollapsed(prev => ({ ...prev, [itemId]: !prev[itemId] }))
  }

  const focusedOps = pending.filter(entry => entry.sid === focused).map(entry => entry.op)
  const board = shown === null ? null : viewBoard(shown.board, focusedOps)
  const items = boardItems(board)
  return jsxs('div', {
    className: 'flex h-full flex-col text-xs',
    children: [
      jsx(Header, { counts: openCounts(items), items }),
      jsx(Notice, { text: noticeText({ meta, notice, loadFailed }) }),
      jsx(ScrollArea, {
        className: LIST_CLASS,
        children: jsx('div', {
          className: LIST_BODY_CLASS,
          children: buildTree(items).map(group =>
            jsx(ItemBlock, { group, collapsed: collapsed[group.item.id] === true, onToggle, onCheck }, group.item.id)
          )
        })
      })
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
  API_VERSION,
  EVENT_TYPE,
  PLUGIN_ID,
  PLUGIN_VERSION,
  LOAD_FAILED_NOTICE,
  NOTICE_MS,
  POLL_MS,
  STALE_NOTICE,
  WRITE_FAILED_NOTICE,
  applyOp,
  boardItems,
  boardMarkdown,
  boardPath,
  buildTree,
  headerText,
  isMismatch,
  isTopLevel,
  noticeText,
  openCounts,
  subtaskCountText,
  viewBoard,
  writeOutcome
}
