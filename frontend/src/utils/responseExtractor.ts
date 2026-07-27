import type { ResponseExtractConfig } from '../types/connector'

export function extractResponse(raw: string, config: ResponseExtractConfig) {
  if (config.type === 'text') return raw
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
  try {
    const parsed = JSON.parse(raw)
    const value = readJsonPath(parsed, config.path) ?? readJsonPath(parsed, config.fallbackPath || '')
    return value == null ? '' : stringifyExtractedValue(value)
  } catch {
    return ''
  }
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

function readJsonPath(value: unknown, path: string) {
  if (!path) return undefined
  const cleanPath = path.replace(/^\$\./, '')
  return cleanPath.split('.').reduce<unknown>((current, key) => {
    if (current && typeof current === 'object') return (current as Record<string, unknown>)[key]
    return undefined
  }, value)
}
