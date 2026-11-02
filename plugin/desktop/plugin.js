/**
 * Session tasks pane for hermes-session-tasks. Plain ESM, loaded uncompiled: UI is jsx() calls.
 * Only three imports resolve here: the plugin SDK, react and the jsx runtime.
 * It shows the focused session's board as checkbox rows and sends Theo's edits through the plugin routes.
 * Only Pane calls React hooks. Every other component is a plain function of its props.
 */

import { Checkbox, host, useValue } from '@hermes/plugin-sdk'
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
const NOTICE_CLASS = 'text-xs text-(--ui-text-secondary)'
const ROW_CLASS = 'flex min-h-8 items-start gap-1 py-1'
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

function Header({ counts }) {
  if (counts.total === 0) return null
  return jsx('div', { className: HEADER_CLASS, children: headerText(counts) })
}

function ItemRow({ item, onCheck }) {
  const textClass = item.checked ? `${TEXT_CLASS} ${DONE_CLASS}` : TEXT_CLASS
  return jsxs('div', {
    className: isTopLevel(item) ? ROW_CLASS : `${ROW_CLASS} pl-6`,
    'data-item-id': String(item.id),
    children: [
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
      })
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
      })
      .catch(() => {})
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
    if (outcome === 'failed') reload()
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

  const focusedOps = pending.filter(entry => entry.sid === focused).map(entry => entry.op)
  const board = shown === null ? null : viewBoard(shown.board, focusedOps)
  const items = boardItems(board)
  return jsxs('div', {
    className: 'flex h-full flex-col gap-2 p-2 text-xs',
    children: [
      jsx(Header, { counts: openCounts(items) }),
      jsx(Notice, { text: noticeText({ meta, notice, loadFailed: false }) }),
      jsx('div', {
        className: 'flex flex-col',
        children: items.map(item => jsx(ItemRow, { item, onCheck }, item.id))
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
  boardPath,
  headerText,
  isMismatch,
  isTopLevel,
  noticeText,
  openCounts,
  viewBoard,
  writeOutcome
}
