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
const EVENT_TYPE = 'plugin.hermes-session-tasks.board.updated'
const MISMATCH_LINE = 'Version mismatch: update the desktop plugin on this machine'
const HEADER_CLASS = 'text-sm font-medium text-(--ui-text-secondary)'
const NOTICE_CLASS = 'text-xs text-(--ui-text-secondary)'
const ROW_CLASS = 'flex min-h-8 items-start gap-1 py-1'
const HIT_CLASS = 'flex size-6 shrink-0 items-center justify-center'
const TEXT_CLASS = 'min-w-0 flex-1 py-1 text-xs'
const DONE_CLASS = 'text-(--ui-text-secondary)'
const TEXT_STYLE = { overflowWrap: 'anywhere', whiteSpace: 'pre-wrap' }
const DONE_STYLE = { ...TEXT_STYLE, textDecoration: 'line-through' }

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

function boardPath(sid) {
  return `/board?session_id=${encodeURIComponent(sid)}`
}

function isMismatch(meta) {
  if (meta === null || meta.ok !== true) return false
  return meta.backend_version !== PLUGIN_VERSION || meta.api_version !== API_VERSION
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
  const shown = server !== null && server.sid === (sid || null) ? server : null
  // The listener, the interval and the write live longer than one render, so they read this ref.
  const current = useRef({ sid: null, rev: null })
  current.current.sid = sid || null
  current.current.rev = shown === null ? null : shown.rev

  function take(asked, reply) {
    if (current.current.sid !== asked) return
    setServer({ sid: asked, rev: reply.rev, root_id: reply.root_id, board: reply.board })
  }

  function reload() {
    const asked = current.current.sid
    if (!asked) return Promise.resolve()
    return ctx
      .rest(boardPath(asked))
      .then(body => {
        if (body && body.ok === true) take(asked, body)
      })
      .catch(() => {})
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
  function onCheck(item, value) {
    const asked = current.current.sid
    const baseRev = current.current.rev
    if (!asked || baseRev === null) return
    const op = { op: 'set_checked', item_id: item.id, checked: value === true }
    setServer(prev =>
      prev !== null && prev.sid === asked ? { ...prev, board: applyOp(prev.board, op) } : prev
    )
    ctx
      .rest('/board/edit', {
        method: 'POST',
        body: { session_id: asked, ops: [op], base_rev: baseRev }
      })
      .then(reply => {
        if (reply && reply.ok === true) take(asked, reply)
        else reload()
      })
      .catch(() => reload())
  }

  const items = boardItems(shown && shown.board)
  return jsxs('div', {
    className: 'flex h-full flex-col gap-2 p-2 text-xs',
    children: [
      isMismatch(meta) ? jsx('div', { className: NOTICE_CLASS, children: MISMATCH_LINE }) : null,
      jsx(Header, { counts: openCounts(items) }),
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
  POLL_MS,
  applyOp,
  boardItems,
  boardPath,
  headerText,
  isMismatch,
  isTopLevel,
  openCounts
}
