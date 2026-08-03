import { moonshotApi } from '../api/moonshot'
import type { ConnectorAIConfigureResult, ConnectorConfig, ConnectorEndpointItem, ConnectorListItem, ConnectorProtocol, ConnectorTestResult, CurrentUser } from '../types/connector'
import type { EndpointCreatePayload } from '../types/moonshot'

const META_KEY = 'oxo-connector-endpoint-meta'
export const CONFIGURABLE_CONNECTOR = 'configurable-app-connector'

export const currentUser: CurrentUser = {
  id: 'user-local',
  name: 'You',
  email: 'you@oxo.local',
}

export const connectorService = {
  async listConnectors() {
    const [types, endpoints] = await Promise.all([
      moonshotApi.getConnectorTypes(),
      moonshotApi.getEndpoints() as Promise<ConnectorEndpointItem[]>,
    ])
    const mergedTypes = Array.from(new Set([...types, CONFIGURABLE_CONNECTOR])).sort()
    return mergedTypes.map((type) => toConnectorGroup(type, endpoints.filter((endpoint) => endpoint.connector_type === type)))
  },

  async getConnector(id: string) {
    return (await this.listConnectors()).find((connector) => connector.id === id)
  },

  async saveConnector(config: ConnectorConfig) {
    config.params.connector_config.description = config.description || ''
    if (config.connector_type === CONFIGURABLE_CONNECTOR) {
      delete (config.params.connector_config as ConnectorConfig['params']['connector_config'] & { auth?: unknown }).auth
      config.token = ''
    }
    normalizeResponseConfig(config.params.connector_config.response)
    normalizePromptTemplates(config)
    const payload: EndpointCreatePayload = {
      name: config.name,
      connector_type: config.connector_type || CONFIGURABLE_CONNECTOR,
      uri: config.uri,
      token: config.token,
      model: config.model,
      max_calls_per_second: config.max_calls_per_second,
      max_concurrency: config.max_concurrency,
      params: config.params,
    }
    let id = config.id
    if (id) await moonshotApi.updateEndpoint(id, payload)
    else id = await moonshotApi.createEndpoint(payload)
    const meta = readMeta()
    meta[id] = { ownerId: currentUser.id, ownerName: currentUser.name, source: 'user-created' }
    writeMeta(meta)
    return id
  },

  async deleteConnector(id: string) {
    await moonshotApi.deleteEndpoint(id)
    const meta = readMeta()
    delete meta[id]
    writeMeta(meta)
  },

  duplicateConnector(connector: ConnectorListItem) {
    const sourceEndpoint = connector.endpoints?.[0]
    const base = sourceEndpoint ? endpointToConfig(sourceEndpoint) : defaultConnectorConfig('http')
    return {
      ...base,
      id: undefined,
      name: `Copy of ${sourceEndpoint?.name || connector.name}`,
      source: 'user-created',
      ownerId: currentUser.id,
      ownerName: currentUser.name,
    } satisfies ConnectorConfig
  },

  async testConnector(config: ConnectorConfig, testPrompt: string): Promise<ConnectorTestResult> {
    return moonshotApi.testConnector(config, testPrompt)
  },

  async configureWithAI(requestInformation: string): Promise<ConnectorAIConfigureResult> {
    return moonshotApi.configureConnectorWithAI(requestInformation)
  },
}

export function defaultConnectorConfig(protocol: ConnectorProtocol = 'http', connectorType = CONFIGURABLE_CONNECTOR): ConnectorConfig {
  return {
    name: '',
    description: '',
    connector_type: connectorType,
    uri: protocol === 'websocket' ? 'wss://api.example.com/chat' : 'https://api.example.com/v1/chat',
    token: '',
    model: 'custom-model',
    source: 'user-created',
    ownerId: currentUser.id,
    ownerName: currentUser.name,
    max_calls_per_second: 10,
    max_concurrency: 1,
    params: {
      timeout: 30,
      connector_config: {
        transport: protocol,
        request: protocol === 'http' ? { method: 'POST', path: '', headers: { 'content-type': 'application/json' }, queryParams: {}, bodyType: 'json', formFields: {}, bodyTemplate: '{"message":"{{ prompt }}"}' } : undefined,
        stream: protocol === 'sse' ? { path: '', method: 'GET', headers: { accept: 'text/event-stream' }, queryParams: { prompt: '{{ prompt }}' }, bodyType: 'none', formFields: {}, bodyTemplate: '', eventField: 'data' } : undefined,
        websocket: protocol === 'websocket' ? { path: '', headers: {}, queryParams: {}, messageTemplate: '{"message":"{{ prompt }}"}', responseMessageField: 'message' } : undefined,
        response: { type: 'json-path', path: '$.output', fallbackPath: '$.choices.0.message.content' },
      },
    },
  }
}

export function applyTemplate(config: ConnectorConfig, protocol: ConnectorProtocol) {
  const next = defaultConnectorConfig(protocol, config.connector_type)
  return { ...config, uri: next.uri, token: config.connector_type === CONFIGURABLE_CONNECTOR ? '' : config.token, params: next.params }
}

export function migrateConnectorProtocol(config: ConnectorConfig, protocol: ConnectorProtocol): ConnectorConfig {
  const current = config.params.connector_config
  if (current.transport === protocol) return config

  const source = current.transport === 'http'
    ? current.request
    : current.transport === 'sse'
      ? current.stream
      : current.websocket
  const headers = { ...(source?.headers || {}) }
  const queryParams = { ...(source?.queryParams || {}) }
  const path = source?.path || ''
  const bodyTemplate = source && 'bodyTemplate' in source
    ? source.bodyTemplate || ''
    : source && 'messageTemplate' in source
      ? source.messageTemplate
      : ''
  const messageTemplate = bodyTemplate || '{"message":"{{ prompt }}"}'
  const bodyType = source && 'bodyType' in source ? source.bodyType || 'json' : 'json'
  const formFields = source && 'formFields' in source ? { ...(source.formFields || {}) } : {}
  const sourceMethod = source && 'method' in source ? source.method : undefined
  const uri = migrateConnectorUriScheme(config.uri, protocol)

  return {
    ...config,
    uri,
    params: {
      ...config.params,
      connector_config: {
        description: current.description,
        transport: protocol,
        request: protocol === 'http'
          ? {
              method: sourceMethod === 'PUT' || sourceMethod === 'PATCH' ? sourceMethod : sourceMethod === 'GET' ? 'GET' : 'POST',
              path,
              headers,
              queryParams,
              bodyType,
              formFields,
              bodyTemplate: messageTemplate,
            }
          : undefined,
        stream: protocol === 'sse'
          ? {
              path,
              method: sourceMethod === 'GET' ? 'GET' : 'POST',
              headers,
              queryParams,
              bodyType,
              formFields,
              bodyTemplate: messageTemplate,
              eventField: current.stream?.eventField || 'data',
              dataPrefix: current.stream?.dataPrefix,
            }
          : undefined,
        websocket: protocol === 'websocket'
          ? {
              path,
              headers,
              queryParams,
              messageTemplate,
              responseMessageField: current.websocket?.responseMessageField || 'message',
            }
          : undefined,
        response: { ...current.response },
      },
    },
  }
}

function migrateConnectorUriScheme(uri: string, protocol: ConnectorProtocol) {
  const trimmed = uri.trim()
  if (protocol === 'websocket') {
    if (trimmed.startsWith('https://')) return `wss://${trimmed.slice('https://'.length)}`
    if (trimmed.startsWith('http://')) return `ws://${trimmed.slice('http://'.length)}`
    return uri
  }
  if (trimmed.startsWith('wss://')) return `https://${trimmed.slice('wss://'.length)}`
  if (trimmed.startsWith('ws://')) return `http://${trimmed.slice('ws://'.length)}`
  return uri
}

export function endpointToConfig(endpoint: ConnectorEndpointItem): ConnectorConfig {
  const params = endpoint.connector_type === CONFIGURABLE_CONNECTOR
    ? normalizeParams(endpoint.params, endpoint.token)
    : (endpoint.params as ConnectorConfig['params'])
  const meta = readMeta()[endpoint.id]
  return {
    id: endpoint.id,
    name: endpoint.name,
    description: typeof params.connector_config?.description === 'string' ? params.connector_config.description : '',
    connector_type: endpoint.connector_type,
    uri: endpoint.uri,
    token: endpoint.connector_type === CONFIGURABLE_CONNECTOR ? '' : endpoint.token || '',
    model: endpoint.model || '',
    source: meta?.source || (endpoint.connector_type === CONFIGURABLE_CONNECTOR ? 'user-created' : 'built-in'),
    ownerId: meta?.ownerId || (endpoint.connector_type === CONFIGURABLE_CONNECTOR ? currentUser.id : 'system'),
    ownerName: meta?.ownerName || (endpoint.connector_type === CONFIGURABLE_CONNECTOR ? currentUser.name : 'System'),
    max_calls_per_second: endpoint.max_calls_per_second || 1,
    max_concurrency: endpoint.max_concurrency || 1,
    params,
  }
}

function toConnectorGroup(type: string, endpoints: ConnectorEndpointItem[]): ConnectorListItem {
  const isConfigurable = type === CONFIGURABLE_CONNECTOR
  const protocol = inferProtocol(type, endpoints)
  const firstEndpoint = endpoints[0]
  const config: ConnectorConfig = firstEndpoint
    ? endpointToConfig(firstEndpoint)
    : {
        ...defaultConnectorConfig(protocol),
        name: type,
        source: isConfigurable ? 'user-created' : 'built-in',
        ownerId: isConfigurable ? currentUser.id : 'system',
        ownerName: isConfigurable ? currentUser.name : 'System',
      }
  const latestDate = endpoints
    .map((endpoint) => endpoint.created_date)
    .filter(Boolean)
    .sort()
    .at(-1)
  const now = new Date().toISOString()
  return {
    id: type,
    name: humanizeConnectorType(type),
    description: isConfigurable ? 'Configurable connector for custom AI applications.' : `${endpoints.length} connector endpoint(s) available.`,
    protocol,
    uri: firstEndpoint?.uri || '-',
    source: isConfigurable ? 'user-created' : 'built-in',
    ownerId: isConfigurable ? currentUser.id : 'system',
    ownerName: isConfigurable ? currentUser.name : 'System',
    createdAt: firstEndpoint?.created_date || now,
    updatedAt: latestDate || firstEndpoint?.created_date || now,
    editable: isConfigurable,
    deletable: false,
    config,
    endpoints,
    endpointCount: endpoints.length,
  }
}

interface LegacyAuthConfig {
  type?: string
  headerName?: string
  username?: string
}

function normalizeParams(params: Record<string, unknown>, legacyToken = '') {
  if (params.connector_config) {
    const normalized = params as ConnectorConfig['params']
    const config = normalized.connector_config
    const timeout = Number(normalized.timeout || 30)
    normalized.timeout = timeout > 1000 ? Math.max(1, Math.round(timeout / 1000)) : Math.max(1, timeout)
    migrateLegacyAuthToHeaders(config, legacyToken)
    config.response ||= { type: 'json-path', path: '$.output' }
    normalizeResponseConfig(config.response)
    if (config.request) {
      config.request.headers ||= { 'content-type': 'application/json' }
      config.request.queryParams ||= {}
      config.request.bodyType ||= 'json'
      config.request.formFields ||= {}
    }
    if (config.stream) {
      config.stream.method ||= 'GET'
      config.stream.headers ||= { accept: 'text/event-stream' }
      config.stream.queryParams ||= {}
      config.stream.bodyType ||= 'none'
      config.stream.formFields ||= {}
      config.stream.bodyTemplate ||= ''
    }
    if (config.websocket) {
      config.websocket.headers ||= {}
      config.websocket.queryParams ||= {}
    }
    return normalized
  }
  return defaultConnectorConfig('http').params
}

function migrateLegacyAuthToHeaders(config: ConnectorConfig['params']['connector_config'], token: string) {
  const legacyCarrier = config as ConnectorConfig['params']['connector_config'] & { auth?: LegacyAuthConfig }
  const auth = legacyCarrier.auth
  delete legacyCarrier.auth
  if (!auth || !token) return
  const request = config.transport === 'http' ? config.request : config.transport === 'sse' ? config.stream : config.websocket
  if (!request) return
  request.headers ||= {}
  const type = String(auth.type || 'none').toLowerCase()
  const headerName = auth.headerName || (type === 'api-key' ? 'x-api-key' : type === 'cookie' ? 'Cookie' : 'Authorization')
  const hasHeader = Object.keys(request.headers).some((name) => name.toLowerCase() === headerName.toLowerCase())
  if (hasHeader) return
  if (type === 'bearer') request.headers[headerName] = `Bearer ${token}`
  else if (type === 'api-key' || type === 'cookie') request.headers[headerName] = token
  else if (type === 'basic') request.headers.Authorization = `Basic ${encodeBasicCredential(`${auth.username || ''}:${token}`)}`
}

function encodeBasicCredential(value: string) {
  const bytes = new TextEncoder().encode(value)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary)
}

function normalizeResponseConfig(response: ConnectorConfig['params']['connector_config']['response']) {
  if (response.type === 'event-data' && response.path?.trim()) response.type = 'json-path'
}

function normalizePromptTemplates(config: ConnectorConfig) {
  const connectorConfig = config.params.connector_config
  if (connectorConfig.request) {
    connectorConfig.request.bodyTemplate = normalizePromptMessageTemplate(connectorConfig.request.bodyTemplate)
  }
  if (connectorConfig.stream) {
    connectorConfig.stream.bodyTemplate = normalizePromptMessageTemplate(connectorConfig.stream.bodyTemplate || '')
  }
  if (connectorConfig.websocket) {
    connectorConfig.websocket.messageTemplate = normalizePromptMessageTemplate(connectorConfig.websocket.messageTemplate || '')
  }
}

export function normalizePromptMessageTemplate(template: string) {
  try {
    const body = JSON.parse(template) as { messages?: unknown[] }
    if (!Array.isArray(body.messages)) return template
    const promptIndex = body.messages.findIndex((item) => /\{\{\s*prompt\s*\}\}/.test(JSON.stringify(item)))
    if (promptIndex < 0 || promptIndex === body.messages.length - 1) return template
    body.messages = body.messages.slice(0, promptIndex + 1)
    return JSON.stringify(body, null, 2)
  } catch {
    return template
  }
}

function inferProtocol(type: string, endpoints: ConnectorEndpointItem[]): ConnectorProtocol {
  const configCarrier = endpoints.find((endpoint) => typeof endpoint.params?.connector_config === 'object')
  const connectorConfig = configCarrier?.params.connector_config
  if (connectorConfig && typeof connectorConfig === 'object' && 'transport' in connectorConfig) return (connectorConfig as { transport: ConnectorProtocol }).transport
  if (type.includes('sse')) return 'sse'
  if (type.includes('websocket')) return 'websocket'
  return 'http'
}

function humanizeConnectorType(value: string) {
  return value.replace(/-connector$/, '').replace(/[-_]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function readMeta(): Record<string, { ownerId: string; ownerName: string; source: 'user-created' }> {
  try {
    return JSON.parse(window.localStorage.getItem(META_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeMeta(value: Record<string, { ownerId: string; ownerName: string; source: 'user-created' }>) {
  window.localStorage.setItem(META_KEY, JSON.stringify(value))
}
