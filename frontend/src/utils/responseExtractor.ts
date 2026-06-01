import type { ResponseExtractConfig } from '../types/connector'

export function extractResponse(raw: string, config: ResponseExtractConfig) {
  if (config.type === 'text') return raw
  if (config.type === 'event-data') {
    const line = raw.split(/\r?\n/).find((item) => item.startsWith('data:'))
    return line ? line.replace(/^data:\s*/, '') : raw
  }
  try {
    const parsed = JSON.parse(raw)
    return String(readJsonPath(parsed, config.path) ?? readJsonPath(parsed, config.fallbackPath || '') ?? '')
  } catch {
    return ''
  }
}

function readJsonPath(value: unknown, path: string) {
  if (!path) return undefined
  const cleanPath = path.replace(/^\$\./, '')
  return cleanPath.split('.').reduce<unknown>((current, key) => {
    if (current && typeof current === 'object') return (current as Record<string, unknown>)[key]
    return undefined
  }, value)
}
