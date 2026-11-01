/**
 * Test pane for hermes-session-tasks. Plain ESM, loaded uncompiled: UI is jsx() calls.
 * Only three imports resolve here: the plugin SDK, react and the jsx runtime.
 * It reads one board through the plugin routes and shows plain text lines.
 */

import { host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const PLUGIN_ID = 'hermes-session-tasks'
const PLUGIN_VERSION = '0.1.0'
const API_VERSION = 1
const POLL_MS = 6000
const EVENT_TYPE = 'plugin.hermes-session-tasks.board.updated'
const TEST_ITEM_TEXT = 'test item added by the pane'
const META_FAILED = { ok: false }
const LINE_CLASS = 'whitespace-pre-wrap break-words text-(--ui-text-secondary)'

function isTopLevel(item) {
  return item.parent_id === null || item.parent_id === undefined
}

function itemLine(item) {
  const indent = isTopLevel(item) ? '' : '  '
  return `${indent}${item.checked ? '[x]' : '[ ]'} #${item.id} ${item.text}`
}

function boardLines(board) {
  const items = board && Array.isArray(board.items) ? board.items : []
  if (items.length === 0) return ['board is empty']
  return items.map(itemLine)
}

function boardPath(sid) {
  return `/board?session_id=${encodeURIComponent(sid)}`
}

function Line({ text }) {
  return jsx('div', { className: LINE_CLASS, children: text })
}

function Pane({ ctx }) {
  const sid = useValue(host.state.focusedStoredSessionId)
  const [meta, setMeta] = useState(null)
  const [reply, setReply] = useState(null)

  useEffect(() => {
    let live = true
    ctx
      .rest('/meta')
      .then(body => live && setMeta(body))
      .catch(() => live && setMeta(META_FAILED))
    return () => {
      live = false
    }
  }, [])

  useEffect(() => {
    if (!sid) {
      setReply(null)
      return undefined
    }
    let live = true
    ctx
      .rest(boardPath(sid))
      .then(body => live && setReply(body))
      .catch(() => {})
    return () => {
      live = false
    }
  }, [sid])

  const reached = meta !== null && meta.ok === true
  const backend = reached ? `backend ${meta.backend_version}, api ${meta.api_version}` : null
  const backendLine = meta === null ? 'backend checking' : backend || 'backend not reached'
  const rev = reply && reply.ok === true ? reply.rev : 'unknown'
  const sessionLine = sid ? `session ${sid}, board rev ${rev}` : 'no session focused'
  const lines = [backendLine, `pane ${PLUGIN_VERSION}, api ${API_VERSION}`, sessionLine]
    .concat(boardLines(reply && reply.board))
  return jsxs('div', {
    className: 'flex h-full flex-col gap-1 p-3 text-sm',
    children: lines.map((text, index) => jsx(Line, { text }, index))
  })
}

export default {
  id: PLUGIN_ID,
  name: 'Session tasks (test)',
  register(ctx) {
    ctx.register({
      id: 'pane',
      area: 'panes',
      title: 'Session tasks',
      data: { placement: 'right', width: '320px' },
      render: () => jsx(Pane, { ctx })
    })
  }
}

export { API_VERSION, EVENT_TYPE, PLUGIN_ID, PLUGIN_VERSION, POLL_MS, TEST_ITEM_TEXT, boardLines }
