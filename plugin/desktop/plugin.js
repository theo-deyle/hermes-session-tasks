/**
 * Test pane for hermes-session-tasks. Plain ESM, loaded uncompiled: UI is jsx() calls.
 * Only three imports resolve here: the plugin SDK, react and the jsx runtime.
 * It reads one board through the plugin routes and shows plain text lines.
 */

import { Button, host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const PLUGIN_ID = 'hermes-session-tasks'
const PLUGIN_VERSION = '0.1.0'
const API_VERSION = 1
const POLL_MS = 6000
const EVENT_TYPE = 'plugin.hermes-session-tasks.board.updated'
const TEST_ITEM_TEXT = 'test item added by the pane'
const metaFailed = error => ({ ok: false, message: String(error && error.message ? error.message : error) })
const MISMATCH_LINE = 'Version mismatch: update the desktop plugin on this machine'
const WRITE_NOT_RUN = 'write test: not run'
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

function eventLine(label, seen) {
  if (!seen) return `${label} event: none yet`
  return `${label} event: rev ${seen.rev} at ${seen.at} (${seen.here ? 'this chat' : 'other chat'})`
}

function staleSummary(reply) {
  if (reply.ok === true) return `ok at rev ${reply.rev}`
  return `${reply.error} (${reply.reason}) at rev ${reply.rev}`
}

function backendLine(meta) {
  if (meta === null) return 'backend checking'
  if (meta.ok !== true) return `backend not reached: ${meta.message || 'no detail'}`
  return `backend ${meta.backend_version}, api ${meta.api_version}`
}

function isMismatch(meta) {
  if (meta === null || meta.ok !== true) return false
  return meta.backend_version !== PLUGIN_VERSION || meta.api_version !== API_VERSION
}

function addOp() {
  return { op: 'add', text: TEST_ITEM_TEXT }
}

function staleOp(item) {
  return { op: 'set_checked', item_id: item.id, checked: true }
}

function Pane({ ctx }) {
  const sid = useValue(host.state.focusedStoredSessionId)
  const [meta, setMeta] = useState(null)
  const [reply, setReply] = useState(null)
  const [agentEvent, setAgentEvent] = useState(null)
  const [paneEvent, setPaneEvent] = useState(null)
  const [writeLine, setWriteLine] = useState(WRITE_NOT_RUN)
  // The listener and the interval live longer than one render, so they read this ref.
  const current = useRef({ sid: null, root: null })
  current.current.sid = sid || null
  current.current.root = reply && reply.ok === true ? reply.root_id : null

  function reload() {
    const asked = current.current.sid
    if (!asked) return Promise.resolve()
    return ctx
      .rest(boardPath(asked))
      .then(body => {
        if (current.current.sid === asked) setReply(body)
      })
      .catch(() => {})
  }

  useEffect(() => {
    let live = true
    ctx
      .rest('/meta')
      .then(body => live && setMeta(body))
      .catch(error => live && setMeta(metaFailed(error)))
    return () => {
      live = false
    }
  }, [])

  useEffect(() => {
    if (!sid) {
      setReply(null)
      return undefined
    }
    reload()
    return ctx.setInterval(reload, POLL_MS)
  }, [sid])

  useEffect(
    () =>
      ctx.onEvent(EVENT_TYPE, event => {
        const payload = (event && event.payload) || {}
        const root = current.current.root
        const here = root !== null && payload.root_id === root
        const seen = { rev: payload.rev, at: new Date().toLocaleTimeString(), here }
        if (payload.actor === 'agent') setAgentEvent(seen)
        if (payload.actor === 'user') setPaneEvent(seen)
        reload()
      }),
    []
  )

  async function runWriteTest() {
    const target = current.current.sid
    if (!target) {
      setWriteLine('write test: no session focused')
      return
    }
    try {
      const first = await ctx.rest('/board/edit', {
        method: 'POST',
        body: { session_id: target, ops: [addOp()] }
      })
      if (first.ok !== true) {
        setWriteLine(`write test: add ${first.error} (${first.reason})`)
      } else {
        // base_rev 0 is behind every existing item, so this write is always answered stale.
        const second = await ctx.rest('/board/edit', {
          method: 'POST',
          body: { session_id: target, ops: [staleOp(first.board.items[0])], base_rev: 0 }
        })
        setWriteLine(`write test: add ok at rev ${first.rev}, stale write answered ${staleSummary(second)}`)
      }
    } catch (error) {
      setWriteLine(`write test: failed (${error && error.message})`)
    }
    await reload()
  }

  const rev = reply && reply.ok === true ? reply.rev : 'unknown'
  const lines = [
    backendLine(meta),
    `pane ${PLUGIN_VERSION}, api ${API_VERSION}`,
    isMismatch(meta) ? MISMATCH_LINE : null,
    sid ? `session ${sid}, board rev ${rev}` : 'no session focused',
    eventLine('agent', agentEvent),
    eventLine('pane', paneEvent),
    writeLine
  ]
    .filter(text => text !== null)
    .concat(boardLines(reply && reply.board))
  return jsxs('div', {
    className: 'flex h-full flex-col gap-2 p-3 text-sm',
    children: [
      jsx('div', {
        className: 'flex flex-col gap-1',
        children: lines.map((text, index) => jsx(Line, { text }, index))
      }),
      jsx(Button, { onClick: runWriteTest, children: 'Run write test' })
    ]
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
      data: { placement: 'right', dock: { pane: 'workspace', pos: 'right' }, width: '320px' },
      render: () => jsx(Pane, { ctx })
    })
  }
}

export { API_VERSION, EVENT_TYPE, PLUGIN_ID, PLUGIN_VERSION, POLL_MS, TEST_ITEM_TEXT, boardLines }
