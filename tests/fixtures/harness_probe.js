/**
 * Harness self-test fixture. It is never installed on a Desktop machine.
 * It is a small plugin that uses the SDK names the pane uses, so the node harness can prove each stub, record and step.
 * Only Probe calls React hooks. Every other component is a plain function of its props.
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

const EVENT_TYPE = 'plugin.hermes-session-tasks.board.updated'

function boardPath(sid) {
  return `/board?session_id=${encodeURIComponent(sid)}`
}

function ItemRow({ item, onClickText, onDelete }) {
  return jsxs('div', {
    'data-item-id': String(item.id),
    children: [
      jsx('span', {
        onMouseDown: event => event.preventDefault(),
        children: jsx(Checkbox, {
          checked: item.checked,
          onCheckedChange: () => {},
          'aria-label': item.text
        })
      }),
      jsx('span', {
        style: { whiteSpace: 'pre-wrap' },
        onClick: () => onClickText(item),
        children: item.text
      }),
      jsx(Tip, {
        label: 'Probe delete',
        children: jsx(Button, {
          'aria-label': 'Probe delete',
          onClick: () => onDelete(item),
          children: jsx(icons.Trash2, {})
        })
      })
    ]
  })
}

function Probe({ ctx }) {
  const sid = useValue(host.state.focusedStoredSessionId)
  // The last accepted board reply: { sid, rev, items }.
  const [server, setServer] = useState(null)
  const [value, setValue] = useState('')
  const [line, setLine] = useState('')
  const [confirmId, setConfirmId] = useState(null)
  const [busy, setBusy] = useState(false)
  const [optimistic, setOptimistic] = useState(null)
  const timerStop = useRef(null)
  const current = useRef({ sid: null, rev: null, value: '', confirmId: null, busy: false })
  current.current.sid = sid || null
  current.current.rev = server === null ? null : server.rev
  current.current.value = value
  current.current.confirmId = confirmId
  current.current.busy = busy

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

  useEffect(() => ctx.onEvent(EVENT_TYPE, () => load()), [])

  // Returns the write promise, or a resolved null when there is nothing to write to.
  function send(op) {
    const asked = current.current.sid
    const baseRev = current.current.rev
    if (!asked || baseRev === null) return Promise.resolve(null)
    return ctx.rest('/board/edit', {
      method: 'POST',
      body: { session_id: asked, ops: [op], base_rev: baseRev }
    })
  }

  // Starts the write and returns nothing: a caller must never wait on the write.
  function add() {
    const text = current.current.value
    if (text === '' || current.current.busy) return
    setBusy(true)
    setOptimistic(text)
    send({ op: 'add', text })
      .then(reply => {
        if (reply && reply.ok === true) setValue('')
      })
      .catch(() => setLine('probe write failed'))
      .then(() => {
        setBusy(false)
        setOptimistic(null)
        return load()
      })
  }

  function confirmRemove() {
    const itemId = current.current.confirmId
    setConfirmId(null)
    if (itemId === null) return
    send({ op: 'remove', item_id: itemId })
      .catch(() => {})
      .then(() => load())
  }

  const items = server !== null && server.sid === (sid || null) ? server.items : []
  return jsxs('div', {
    children: [
      jsx('div', { className: 'probe-header', children: 'Probe header' }),
      jsxs(ScrollArea, {
        className: 'probe-scroll',
        children: [
          ...items.map(item =>
            jsx(
              ItemRow,
              {
                item,
                onClickText: clicked => setLine(`probe clicked ${clicked.text}`),
                onDelete: removed => setConfirmId(removed.id)
              },
              item.id
            )
          ),
          items.length === 0
            ? jsx(EmptyState, { title: 'Probe empty', description: 'Probe empty body' })
            : null
        ]
      }),
      sid ? jsx('div', { children: `probe session ${sid}` }) : null,
      optimistic === null ? null : jsx('div', { children: optimistic }),
      line === '' ? null : jsx('div', { children: line }),
      jsx(Button, {
        onClick: () => {
          timerStop.current = ctx.setTimeout(() => setLine('probe timer fired'), 4000)
        },
        children: 'Probe timer'
      }),
      jsx(Button, {
        onClick: () => {
          const stop = ctx.setTimeout(() => setLine('probe timer fired'), 4000)
          stop()
        },
        children: 'Probe timer cancel'
      }),
      jsx(Button, { disabled: items.length === 0, onClick: () => {}, children: 'Probe copy all' }),
      jsx(CopyButton, {
        appearance: 'icon',
        label: 'Probe copy',
        text: () => `probe copy ${items.length}`,
        disabled: items.length === 0
      }),
      jsx(Input, {
        placeholder: 'Probe add',
        value,
        readOnly: busy,
        onChange: event => setValue(event.target.value),
        onKeyDown: event => {
          if (event.key === 'Enter') add()
          if (event.key === 'Escape') setValue('')
        },
        onBlur: () => setLine('probe blurred')
      }),
      jsx(ConfirmDialog, {
        open: confirmId !== null,
        title: 'Probe confirm',
        description: 'Probe body',
        confirmLabel: 'Probe yes',
        cancelLabel: 'Probe no',
        destructive: true,
        onClose: () => setConfirmId(null),
        onConfirm: confirmRemove
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
