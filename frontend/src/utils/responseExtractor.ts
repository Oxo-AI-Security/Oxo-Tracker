import type { ResponseExtractConfig } from '../types/connector'

export function extractResponse(raw: string, config: ResponseExtractConfig) {
  if (config.type === 'text') return raw
  if (config.type === 'text-fragment') {
    const inferredPath = findJsonPathContaining(config.sampleResponse || '', '{{ output }}')
    if (inferredPath) config = { ...config, type: 'json-path', path: inferredPath }
    else return extractTextFragment(raw, config) ?? raw
  }
  const payloads = eventPayloads(raw)
  if (config.type === 'event-data' && !config.path) {
    return payloads.length ? payloads.join('') : raw
  }
  for (const path of [config.path, config.fallbackPath]) {
    if (!path) continue
    const streamedValues = payloads.flatMap((payload) => {
      try {
        const value = readJsonPath(JSON.parse(payload), path)
        return value == null ? [] : [stringifyExtractedValue(value)]
      } catch {
        return []
      }
    })
    if (streamedValues.length) return streamedValues.join('')
  }
  const documents = parseJsonDocuments(raw)
  for (const parsed of [...documents].reverse()) {
    const value = readJsonPath(parsed, config.path) ?? readJsonPath(parsed, config.fallbackPath || '')
    if (value != null) return stringifyExtractedValue(value)
  }
  return documents.length ? '' : raw
}

function eventPayloads(raw: string) {
  return raw
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.replace(/^data:\s*/, '').trim())
    .filter((payload) => payload && payload !== '[DONE]')
}

function stringifyExtractedValue(value: unknown) {
  return typeof value === 'string' ? value : typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function extractTextFragment(raw: string, config: ResponseExtractConfig) {
  const prefix = config.prefix || ''
  const suffix = config.suffix || ''
  if (prefix && raw.includes(prefix)) {
    const start = raw.indexOf(prefix) + prefix.length
    const end = suffix ? raw.indexOf(suffix, start) : -1
    return end >= 0 ? raw.slice(start, end) : raw.slice(start)
  }
  return config.selectedText && raw.includes(config.selectedText) ? config.selectedText : undefined
}

export function parseJsonDocuments(raw: string): unknown[] {
  const trimmed = raw.trim()
  if (!trimmed) return []
  try {
    return [JSON.parse(trimmed)]
  } catch {
    // Continue with a framing-aware scan for concatenated JSON documents.
  }

  const documents: unknown[] = []
  let start = -1
  let depth = 0
  let inString = false
  let escaped = false
  for (let index = 0; index < raw.length; index += 1) {
    const character = raw[index]
    if (start < 0) {
      if (/\s/.test(character)) continue
      if (character !== '{' && character !== '[') return []
      start = index
    }
    if (inString) {
      if (escaped) escaped = false
      else if (character === '\\') escaped = true
      else if (character === '"') inString = false
      continue
    }
    if (character === '"') {
      inString = true
      continue
    }
    if (character === '{' || character === '[') depth += 1
    else if (character === '}' || character === ']') depth -= 1
    if (depth < 0) return []
    if (depth === 0 && start >= 0) {
      try {
        documents.push(JSON.parse(raw.slice(start, index + 1)))
      } catch {
        return []
      }
      start = -1
    }
  }
  return depth === 0 && !inString && start < 0 ? documents : []
}

export function findJsonPathContaining(raw: string, marker: string) {
  const walk = (value: unknown, path = '$'): string | undefined => {
    if (Array.isArray(value)) {
      for (let index = 0; index < value.length; index += 1) {
        const found = walk(value[index], `${path}.${index}`)
        if (found) return found
      }
      return undefined
    }
    if (value && typeof value === 'object') {
      for (const [key, child] of Object.entries(value)) {
        const found = walk(child, `${path}.${key}`)
        if (found) return found
      }
      return undefined
    }
    return String(value ?? '').includes(marker) ? path : undefined
  }
  for (const document of [...parseJsonDocuments(raw)].reverse()) {
    const found = walk(document)
    if (found) return found
  }
  return undefined
}

function readJsonPath(value: unknown, path: string) {
  if (!path) return undefined
  const cleanPath = path.replace(/^\$\./, '')
  return cleanPath.split('.').reduce<unknown>((current, key) => {
    if (current && typeof current === 'object') return (current as Record<string, unknown>)[key]
    return undefined
  }, value)
}
