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
  const current = useRef({ sid: null, rev: null, value: '', confirmId: null })
  current.current.sid = sid || null
  current.current.rev = server === null ? null : server.rev
  current.current.value = value
  current.current.confirmId = confirmId

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
  function write(op, onOk) {
    const asked = current.current.sid
    const baseRev = current.current.rev
    if (!asked || baseRev === null) return
    ctx
      .rest('/board/edit', {
        method: 'POST',
        body: { session_id: asked, ops: [op], base_rev: baseRev }
      })
      .then(reply => {
        if (reply && reply.ok === true) onOk()
        return load()
      })
      .catch(() => load())
  }

  function add() {
    const text = current.current.value
    if (text === '') return
    write({ op: 'add', text }, () => setValue(''))
  }

  function confirmRemove() {
    const itemId = current.current.confirmId
    setConfirmId(null)
    if (itemId === null) return
    write({ op: 'remove', item_id: itemId }, () => {})
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
      line === '' ? null : jsx('div', { children: line }),
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
