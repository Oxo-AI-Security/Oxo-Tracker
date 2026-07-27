export interface SseEventDetail {
  index: number
  event: string
  id?: string
  retry?: string
  data: string
  parsedData?: unknown
  terminal: boolean
}

export interface SseResponsePreview {
  raw: string
  events: SseEventDetail[]
  mergedSample: string
  mode: 'json' | 'event-data'
  parsedEventCount: number
  plainEventCount: number
  terminalEventCount: number
}

interface PendingSseEvent {
  event?: string
  id?: string
  retry?: string
  dataLines: string[]
  touched: boolean
}

function createPendingEvent(): PendingSseEvent {
  return {
    dataLines: [],
    touched: false,
  }
}

function cloneValue<T>(value: T): T {
  if (value === undefined) return value
  return JSON.parse(JSON.stringify(value)) as T
}

function mergeStreamValue(current: unknown, incoming: unknown): unknown {
  if (current === undefined || current === null) return cloneValue(incoming)
  if (incoming === undefined || incoming === null) return current

  if (typeof current === 'string' && typeof incoming === 'string') {
    return `${current}${incoming}`
  }

  if (Array.isArray(current) && Array.isArray(incoming)) {
    const merged = current.map((value) => cloneValue(value))
    incoming.forEach((value, index) => {
      merged[index] = mergeStreamValue(merged[index], value)
    })
    return merged
  }

  if (
    typeof current === 'object'
    && !Array.isArray(current)
    && typeof incoming === 'object'
    && !Array.isArray(incoming)
  ) {
    const merged: Record<string, unknown> = { ...(current as Record<string, unknown>) }
    Object.entries(incoming as Record<string, unknown>).forEach(([key, value]) => {
      merged[key] = mergeStreamValue(merged[key], value)
    })
    return merged
  }

  return cloneValue(incoming)
}

export function parseSseEvents(raw: string): SseEventDetail[] {
  const events: SseEventDetail[] = []
  let pending = createPendingEvent()

  const flush = () => {
    if (!pending.touched && pending.dataLines.length === 0) return
    const data = pending.dataLines.join('\n')
    let parsedData: unknown
    if (data && data !== '[DONE]') {
      try {
        parsedData = JSON.parse(data)
      } catch {
        parsedData = undefined
      }
    }
    const eventName = pending.event || 'message'
    events.push({
      index: events.length + 1,
      event: eventName,
      id: pending.id,
      retry: pending.retry,
      data,
      parsedData,
      terminal: data === '[DONE]' || eventName.toLowerCase() === 'done',
    })
    pending = createPendingEvent()
  }

  raw.replace(/\r\n?/g, '\n').split('\n').forEach((line) => {
    if (!line) {
      flush()
      return
    }
    if (line.startsWith(':')) {
      pending.touched = true
      return
    }

    const separator = line.indexOf(':')
    const field = separator >= 0 ? line.slice(0, separator) : line
    let value = separator >= 0 ? line.slice(separator + 1) : ''
    if (value.startsWith(' ')) value = value.slice(1)
    pending.touched = true

    if (field === 'data') pending.dataLines.push(value)
    if (field === 'event') pending.event = value
    if (field === 'id') pending.id = value
    if (field === 'retry') pending.retry = value
  })
  flush()

  if (events.length === 0 && raw.trim()) {
    const data = raw.trim()
    let parsedData: unknown
    try {
      parsedData = JSON.parse(data)
    } catch {
      parsedData = undefined
    }
    events.push({
      index: 1,
      event: 'message',
      data,
      parsedData,
      terminal: false,
    })
  }

  return events
}

export function buildSseResponsePreview(raw: string): SseResponsePreview {
  const events = parseSseEvents(raw)
  let mergedJson: unknown
  let plainText = ''
  let parsedEventCount = 0
  let plainEventCount = 0
  let terminalEventCount = 0

  events.forEach((event) => {
    if (event.terminal) {
      terminalEventCount += 1
      return
    }
    if (event.parsedData !== undefined) {
      mergedJson = mergeStreamValue(mergedJson, event.parsedData)
      parsedEventCount += 1
      return
    }
    if (event.data) {
      plainText += event.data
      plainEventCount += 1
    }
  })

  const mode = parsedEventCount > 0 ? 'json' : 'event-data'
  const mergedValue = mode === 'json' ? mergedJson : { data: plainText }
  const mergedSample = JSON.stringify(mergedValue ?? {}, null, 2)

  return {
    raw,
    events,
    mergedSample,
    mode,
    parsedEventCount,
    plainEventCount,
    terminalEventCount,
  }
}

export function formatSseEventData(event: SseEventDetail): string {
  if (event.parsedData !== undefined) return JSON.stringify(event.parsedData, null, 2)
  return event.data || '(empty data)'
}
