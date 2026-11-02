// Node VM harness for plugin/desktop/plugin.js.
//
// Usage: node --experimental-vm-modules tests/desktop_pane_harness.mjs <plugin.js> <config.json>
//
// It loads the plugin with stub SDK, react and jsx-runtime modules, runs the registered
// pane through a small hook runtime, and prints one JSON line:
//   lines, restCalls, contribution, intervals, eventTypes, buttons, checkboxes.
//
// Config keys:
//   baseUrl       relay URL; ctx.rest forwards to baseUrl + path with fetch
//   focused       the focused stored session id, or null
//   restOverrides map of path to a reply body, or the string "__error__" to reject
//   steps         list of {"click": "<button label>"}, {"event": {...}} or
//                 {"check": {"row": "<data-item-id>", "value": true|false}}
//
// A checkbox is recorded as {row, label, checked, disabled}. `row` is the data-item-id of the
// nearest ancestor host element, or null.

import fs from 'node:fs/promises'
import process from 'node:process'
import vm from 'node:vm'

const MAX_ROUNDS = 40
const SETTLE_MS = 15

const pluginPath = process.argv[2]
const configPath = process.argv[3]
if (!pluginPath || !configPath) throw new Error('usage: <plugin.js> <config.json>')

const config = JSON.parse(await fs.readFile(configPath, 'utf8'))
const source = await fs.readFile(pluginPath, 'utf8')
const overrides = config.restOverrides ?? {}
const steps = config.steps ?? []

const restCalls = []
const intervals = []
const eventTypes = []
const listeners = []
let contribution = null
let activity = false
let pending = 0

// ---- hook runtime: one component tree, slots by call order ----
const slots = []
let slotIndex = 0
let componentDepth = 0

// The runtime keeps one slot list by call order, so a hook in a child that renders conditionally would read another slot.
function assertTopLevel() {
  if (componentDepth !== 1) throw new Error('hooks run only in the top-level pane component')
}
let queuedEffects = []

function depsChanged(before, after) {
  if (!before || !after) return true
  return before.length !== after.length || before.some((value, i) => !Object.is(value, after[i]))
}

function useState(initial) {
  assertTopLevel()
  const index = slotIndex++
  if (!slots[index]) {
    slots[index] = { value: typeof initial === 'function' ? initial() : initial }
    slots[index].set = next => {
      const value = typeof next === 'function' ? next(slots[index].value) : next
      if (!Object.is(value, slots[index].value)) {
        slots[index].value = value
        activity = true
      }
    }
  }
  return [slots[index].value, slots[index].set]
}

function useRef(initial) {
  assertTopLevel()
  const index = slotIndex++
  if (!slots[index]) slots[index] = { current: initial }
  return slots[index]
}

function useMemo(factory, deps) {
  assertTopLevel()
  const index = slotIndex++
  if (!slots[index] || depsChanged(slots[index].deps, deps)) slots[index] = { deps, value: factory() }
  return slots[index].value
}

function useCallback(fn, deps) {
  assertTopLevel()
  return useMemo(() => fn, deps)
}

function useEffect(effect, deps) {
  assertTopLevel()
  const index = slotIndex++
  if (!slots[index]) slots[index] = { deps: undefined, cleanup: undefined, fresh: true }
  const slot = slots[index]
  if (slot.fresh || depsChanged(slot.deps, deps)) {
    slot.fresh = false
    slot.deps = deps
    queuedEffects.push(slot.run = () => {
      if (typeof slot.cleanup === 'function') slot.cleanup()
      slot.cleanup = effect()
    })
  }
}

// ---- stub modules ----
function Button() {}
function Checkbox() {}
function Input() {}
function ConfirmDialog() {}
function CopyButton() {}
function EmptyState() {}
function ScrollArea() {}
function Tip() {}
function IconStub() {}
const icons = { Trash2: IconStub, Plus: IconStub, ChevronRight: IconStub, ChevronDown: IconStub }
const focusedAtom = { get: () => config.focused ?? null }
const sdkValues = {
  Button,
  Checkbox,
  ConfirmDialog,
  CopyButton,
  EmptyState,
  Input,
  ScrollArea,
  Tip,
  cn: (...values) => values.filter(Boolean).join(' '),
  host: { state: { focusedStoredSessionId: focusedAtom } },
  icons,
  useValue: atom => atom.get()
}
const Fragment = Symbol.for('react.fragment')
const reactValues = { Fragment, useCallback, useEffect, useMemo, useRef, useState }
const element = (type, props, key) => ({ type, props: props ?? {}, key })
const runtimeValues = { Fragment, jsx: element, jsxs: element }

const context = vm.createContext({ URL, URLSearchParams, console })

function synthetic(identifier, values) {
  const names = Object.keys(values)
  return new vm.SyntheticModule(
    names,
    function initialize() {
      for (const name of names) this.setExport(name, values[name])
    },
    { context, identifier }
  )
}

const dependencies = {
  '@hermes/plugin-sdk': synthetic('@hermes/plugin-sdk', sdkValues),
  react: synthetic('react', reactValues),
  'react/jsx-runtime': synthetic('react/jsx-runtime', runtimeValues)
}

const module = new vm.SourceTextModule(source, { context, identifier: pluginPath })
await module.link(async specifier => {
  const dependency = dependencies[specifier]
  if (!dependency) throw new Error(`unsupported import: ${specifier}`)
  return dependency
})
await module.evaluate()

// ---- ctx stub ----
async function rest(path, options = {}) {
  const method = options.method ?? 'GET'
  restCalls.push({ method, path, body: options.body ?? null })
  activity = true
  pending += 1
  try {
    if (Object.hasOwn(overrides, path)) {
      if (overrides[path] === '__error__') throw new Error('500: forced failure')
      return overrides[path]
    }
    const init = { method, headers: { 'Content-Type': 'application/json' } }
    if (options.body !== undefined) init.body = JSON.stringify(options.body)
    const response = await fetch(config.baseUrl + path, init)
    const text = await response.text()
    if (!response.ok) throw new Error(`${response.status}: ${text}`)
    return JSON.parse(text)
  } finally {
    pending -= 1
  }
}

const ctx = {
  register: value => {
    contribution = value
    return () => {}
  },
  rest,
  onEvent: (type, fn) => {
    eventTypes.push(type)
    const entry = { type, fn }
    listeners.push(entry)
    return () => {
      const at = listeners.indexOf(entry)
      if (at >= 0) listeners.splice(at, 1)
    }
  },
  setInterval: (fn, ms) => {
    intervals.push(ms)
    return () => {}
  },
  setTimeout: () => () => {},
  onDispose: () => {}
}

const plugin = module.namespace.default
if (!plugin || typeof plugin.register !== 'function') {
  throw new Error('the plugin must default-export an object with register(ctx)')
}
plugin.register(ctx)
if (!contribution || typeof contribution.render !== 'function') {
  throw new Error('the plugin must register one contribution with a render function')
}

// ---- render walk ----
// `out` holds the lists one render fills. `here` is {row, scroll, guard} and grows with each host element.
// A stub type is never called as a component: each stub has its own case before the function case.
function walk(node, out, here) {
  if (node === null || node === undefined || typeof node === 'boolean') return
  if (Array.isArray(node)) {
    for (const child of node) walk(child, out, here)
    return
  }
  if (typeof node !== 'object') return
  const { type, props } = node
  if (type === Button) {
    out.buttons.push({
      label: props['aria-label'] ?? textOf(props.children),
      row: here.row,
      disabled: props.disabled === true,
      className: props.className ?? null,
      onClick: props.onClick
    })
    return
  }
  if (type === Checkbox) {
    out.boxes.push({
      row: here.row,
      label: props['aria-label'],
      checked: props.checked === true,
      disabled: props.disabled === true,
      guarded: here.guard,
      onCheckedChange: props.onCheckedChange
    })
    return
  }
  if (type === Input) {
    out.inputs.push({
      placeholder: props.placeholder ?? null,
      row: here.row,
      value: props.value ?? '',
      readOnly: props.readOnly === true,
      disabled: props.disabled === true,
      maxLength: props.maxLength ?? null,
      size: props.size ?? null,
      autoFocus: props.autoFocus === true,
      onChange: props.onChange,
      onKeyDown: props.onKeyDown,
      onBlur: props.onBlur,
      onFocus: props.onFocus
    })
    return
  }
  if (type === ScrollArea) {
    walk(props.children, out, { ...here, scroll: true })
    return
  }
  if (type === Tip) {
    out.tips.push(props.label)
    walk(props.children, out, here)
    return
  }
  if (type === ConfirmDialog) {
    out.confirm = {
      open: props.open === true,
      title: props.title ?? null,
      description: props.description ?? null,
      confirmLabel: props.confirmLabel ?? null,
      cancelLabel: props.cancelLabel ?? null,
      destructive: props.destructive === true,
      onConfirm: props.onConfirm,
      onClose: props.onClose
    }
    return
  }
  if (type === CopyButton) {
    out.copy = {
      text: typeof props.text === 'function' ? props.text() : (props.text ?? null),
      disabled: props.disabled === true,
      label: props.label ?? null,
      appearance: props.appearance ?? null
    }
    return
  }
  if (type === EmptyState) {
    for (const text of [props.title, props.description]) {
      if (typeof text !== 'string') continue
      out.lines.push(text)
      out.nodes.push({ text, className: null, style: null, row: here.row, scroll: here.scroll })
    }
    return
  }
  if (Object.values(icons).includes(type)) return
  if (typeof type === 'function') {
    componentDepth += 1
    try {
      walk(type(props), out, here)
    } finally {
      componentDepth -= 1
    }
    return
  }
  const isHost = typeof type === 'string'
  const itemId = props['data-item-id']
  let next = isHost && itemId !== undefined ? { ...here, row: String(itemId) } : here
  if (isHost && typeof props.onMouseDown === 'function') {
    // Pane mouse-down handlers must only prevent the default, so calling one here has no other effect.
    let prevented = false
    props.onMouseDown({
      preventDefault: () => {
        prevented = true
      }
    })
    next = { ...next, guard: prevented }
  }
  const children = props.children
  const list = Array.isArray(children) ? children : [children]
  const text = list.filter(child => typeof child === 'string' || typeof child === 'number')
  if (isHost && text.length > 0) {
    const joined = text.join('')
    out.lines.push(joined)
    out.nodes.push({
      text: joined,
      className: props.className ?? null,
      style: props.style ?? null,
      row: next.row,
      scroll: next.scroll
    })
    if (typeof props.onClick === 'function') out.clickables.push({ text: joined, onClick: props.onClick })
  }
  walk(list, out, next)
}

function textOf(children) {
  const list = Array.isArray(children) ? children : [children]
  return list.filter(child => typeof child === 'string').join('')
}

let lines = []
let buttons = []
let checkboxes = []
let inputs = []
let nodes = []
let tips = []
let confirmRecord = null
let copyRecord = null
let clickables = []

function renderOnce() {
  slotIndex = 0
  queuedEffects = []
  const out = {
    lines: [],
    buttons: [],
    boxes: [],
    inputs: [],
    nodes: [],
    tips: [],
    clickables: [],
    confirm: null,
    copy: null
  }
  walk(contribution.render(), out, { row: null, scroll: false, guard: false })
  const effects = queuedEffects
  queuedEffects = []
  for (const run of effects) run()
  const changed = JSON.stringify(out.lines) !== JSON.stringify(lines)
  lines = out.lines
  buttons = out.buttons
  checkboxes = out.boxes
  inputs = out.inputs
  nodes = out.nodes
  tips = out.tips
  clickables = out.clickables
  confirmRecord = out.confirm
  copyRecord = out.copy
  return changed
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

async function settle() {
  for (let round = 0; round < MAX_ROUNDS; round += 1) {
    activity = false
    const changed = renderOnce()
    do {
      await sleep(SETTLE_MS)
    } while (pending > 0)
    if (!changed && !activity) return
  }
  throw new Error(`the pane did not settle in ${MAX_ROUNDS} rounds`)
}

// An Input selector is an object with `placeholder` and or `row`. It must match exactly one Input.
function findInput(selector) {
  const wanted = selector ?? {}
  const matches = inputs.filter(
    entry =>
      (wanted.placeholder === undefined || entry.placeholder === wanted.placeholder) &&
      (wanted.row === undefined || entry.row === wanted.row)
  )
  if (matches.length === 0) throw new Error(`no input matches ${JSON.stringify(wanted)}`)
  if (matches.length > 1) {
    throw new Error(`${matches.length} inputs match ${JSON.stringify(wanted)}`)
  }
  return matches[0]
}

// A click step is a label, or {label, row}. It must match exactly one enabled Button.
function findButton(selector) {
  const wanted = typeof selector === 'string' ? { label: selector } : selector
  const matches = buttons.filter(
    entry => entry.label === wanted.label && (wanted.row === undefined || entry.row === wanted.row)
  )
  const where = wanted.row === undefined ? '' : ` in row ${wanted.row}`
  if (matches.length === 0) throw new Error(`no button labelled ${JSON.stringify(wanted.label)}${where}`)
  if (matches.length > 1) {
    throw new Error(`${matches.length} buttons labelled ${JSON.stringify(wanted.label)}${where}`)
  }
  if (matches[0].disabled) throw new Error(`button ${JSON.stringify(wanted.label)} is disabled`)
  return matches[0]
}

function findClickable(text) {
  const matches = clickables.filter(entry => entry.text === text)
  if (matches.length === 0) throw new Error(`no clickable text ${JSON.stringify(text)}`)
  if (matches.length > 1) throw new Error(`${matches.length} clickable texts ${JSON.stringify(text)}`)
  return matches[0]
}

function openDialog() {
  if (confirmRecord === null || !confirmRecord.open) throw new Error('no confirm dialog is open')
  return confirmRecord
}

await settle()
for (const step of steps) {
  if (step.click !== undefined) {
    await findButton(step.click).onClick()
  } else if (step.clickText !== undefined) {
    await findClickable(step.clickText).onClick()
  } else if (step.blur !== undefined) {
    await findInput(step.blur).onBlur({})
  } else if (step.confirm !== undefined) {
    await openDialog().onConfirm()
  } else if (step.cancel !== undefined) {
    await openDialog().onClose()
  } else if (step.check !== undefined) {
    const { row, value } = step.check
    const matches = checkboxes.filter(entry => entry.row === row)
    if (matches.length === 0) throw new Error(`no checkbox in row ${row}`)
    if (matches.length > 1) throw new Error(`${matches.length} checkboxes in row ${row}`)
    await matches[0].onCheckedChange(value)
  } else if (step.type !== undefined) {
    await findInput(step.type.input).onChange({ target: { value: step.type.text } })
  } else if (step.key !== undefined) {
    const record = findInput(step.key.input)
    await record.onKeyDown({
      key: step.key.key,
      preventDefault() {},
      nativeEvent: { isComposing: false }
    })
    if (step.key.blur === true) await record.onBlur({})
  } else if (step.event !== undefined) {
    for (const entry of [...listeners]) {
      if (entry.type === step.event.type) await entry.fn(step.event)
    }
  } else {
    throw new Error(`unknown step ${JSON.stringify(step)}`)
  }
  await settle()
}

function stripHandlers(record) {
  const { onConfirm, onClose, ...rest } = record
  return rest
}

const output = {
  name: plugin.name,
  lines,
  restCalls,
  contribution: {
    id: contribution.id,
    area: contribution.area,
    title: contribution.title,
    data: contribution.data
  },
  intervals,
  eventTypes,
  buttons: buttons.map(({ onClick, ...rest }) => rest),
  checkboxes: checkboxes.map(({ onCheckedChange, ...rest }) => rest),
  inputs: inputs.map(({ onChange, onKeyDown, onBlur, onFocus, ...rest }) => rest),
  confirm: confirmRecord === null ? null : stripHandlers(confirmRecord),
  copy: copyRecord,
  tips,
  nodes
}
process.stdout.write(`${JSON.stringify(output)}\n`, () => process.exit(0))
