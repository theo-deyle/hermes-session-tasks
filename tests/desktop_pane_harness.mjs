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
const focusedAtom = { get: () => config.focused ?? null }
const sdkValues = {
  Button,
  Checkbox,
  cn: (...values) => values.filter(Boolean).join(' '),
  host: { state: { focusedStoredSessionId: focusedAtom } },
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
function walk(node, lines, buttons, boxes, row) {
  if (node === null || node === undefined || typeof node === 'boolean') return
  if (Array.isArray(node)) {
    for (const child of node) walk(child, lines, buttons, boxes, row)
    return
  }
  if (typeof node !== 'object') return
  const { type, props } = node
  if (type === Button) {
    buttons.push({ label: textOf(props.children), onClick: props.onClick })
    return
  }
  if (type === Checkbox) {
    boxes.push({
      row,
      label: props['aria-label'],
      checked: props.checked === true,
      disabled: props.disabled === true,
      onCheckedChange: props.onCheckedChange
    })
    return
  }
  if (typeof type === 'function') {
    componentDepth += 1
    try {
      walk(type(props), lines, buttons, boxes, row)
    } finally {
      componentDepth -= 1
    }
    return
  }
  const itemId = props['data-item-id']
  const here = typeof type === 'string' && itemId !== undefined ? String(itemId) : row
  const children = props.children
  const list = Array.isArray(children) ? children : [children]
  const text = list.filter(child => typeof child === 'string' || typeof child === 'number')
  if (typeof type === 'string' && text.length > 0) lines.push(text.join(''))
  walk(list, lines, buttons, boxes, here)
}

function textOf(children) {
  const list = Array.isArray(children) ? children : [children]
  return list.filter(child => typeof child === 'string').join('')
}

let lines = []
let buttons = []
let checkboxes = []

function renderOnce() {
  slotIndex = 0
  queuedEffects = []
  const nextLines = []
  const nextButtons = []
  const nextBoxes = []
  walk(contribution.render(), nextLines, nextButtons, nextBoxes, null)
  const effects = queuedEffects
  queuedEffects = []
  for (const run of effects) run()
  const changed = JSON.stringify(nextLines) !== JSON.stringify(lines)
  lines = nextLines
  buttons = nextButtons
  checkboxes = nextBoxes
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

await settle()
for (const step of steps) {
  if (step.click !== undefined) {
    const button = buttons.find(entry => entry.label === step.click)
    if (!button) throw new Error(`no button labelled ${JSON.stringify(step.click)}`)
    await button.onClick()
  } else if (step.check !== undefined) {
    const { row, value } = step.check
    const matches = checkboxes.filter(entry => entry.row === row)
    if (matches.length === 0) throw new Error(`no checkbox in row ${row}`)
    if (matches.length > 1) throw new Error(`${matches.length} checkboxes in row ${row}`)
    await matches[0].onCheckedChange(value)
  } else if (step.event !== undefined) {
    for (const entry of [...listeners]) {
      if (entry.type === step.event.type) await entry.fn(step.event)
    }
  } else {
    throw new Error(`unknown step ${JSON.stringify(step)}`)
  }
  await settle()
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
  buttons: buttons.map(entry => entry.label),
  checkboxes: checkboxes.map(({ onCheckedChange, ...rest }) => rest)
}
process.stdout.write(`${JSON.stringify(output)}\n`, () => process.exit(0))
