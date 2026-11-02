/**
 * Harness self-test fixture. It is never installed on a Desktop machine.
 * It is a small plugin that uses the SDK names the pane uses, so the node harness can prove each stub, record and step.
 * Only Probe calls React hooks. Every other component is a plain function of its props.
 */

import { Input, host, useValue } from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

function boardPath(sid) {
  return `/board?session_id=${encodeURIComponent(sid)}`
}

function Probe({ ctx }) {
  const sid = useValue(host.state.focusedStoredSessionId)
  // The last accepted board reply: { sid, rev, items }.
  const [server, setServer] = useState(null)
  const [value, setValue] = useState('')
  const current = useRef({ sid: null, rev: null, value: '' })
  current.current.sid = sid || null
  current.current.rev = server === null ? null : server.rev
  current.current.value = value

  function load() {
    const asked = current.current.sid
    if (!asked) return Promise.resolve()
    return ctx
      .rest(boardPath(asked))
      .then(body => {
        if (body && body.ok === true && current.current.sid === asked) {
          setServer({ sid: asked, rev: body.rev, items: body.board.items })
        }
      })
      .catch(() => {})
  }

  useEffect(() => {
    if (!sid) {
      setServer(null)
      return
    }
    load()
  }, [sid])

  // Starts the write and returns nothing: a caller must never wait on the write.
  function add() {
    const asked = current.current.sid
    const baseRev = current.current.rev
    const text = current.current.value
    if (!asked || baseRev === null || text === '') return
    ctx
      .rest('/board/edit', {
        method: 'POST',
        body: { session_id: asked, ops: [{ op: 'add', text }], base_rev: baseRev }
      })
      .then(reply => {
        if (reply && reply.ok === true) setValue('')
        return load()
      })
      .catch(() => load())
  }

  const items = server !== null && server.sid === (sid || null) ? server.items : []
  return jsxs('div', {
    children: [
      ...items.map(item => jsx('div', { children: item.text }, item.id)),
      jsx(Input, {
        placeholder: 'Probe add',
        value,
        onChange: event => setValue(event.target.value),
        onKeyDown: event => {
          if (event.key === 'Enter') add()
        }
      })
    ]
  })
}

export default {
  id: 'harness-probe',
  name: 'Harness probe',
  register(ctx) {
    ctx.register({
      id: 'pane',
      area: 'panes',
      title: 'Harness probe',
      data: { placement: 'right', width: '320px' },
      render: () => jsx(Probe, { ctx })
    })
  }
}
