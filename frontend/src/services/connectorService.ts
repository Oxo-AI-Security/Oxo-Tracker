import { moonshotApi } from '../api/moonshot'
import type { ConnectorConfig, ConnectorEndpointItem, ConnectorListItem, ConnectorProtocol, ConnectorTestResult, CurrentUser } from '../types/connector'
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
      timeout: 30000,
      connector_config: {
        transport: protocol,
        auth: { type: 'bearer', secretRef: 'CUSTOM_APP_TOKEN' },
        request: protocol === 'http' ? { method: 'POST', path: '', headers: { 'content-type': 'application/json' }, bodyTemplate: '{"message":"{{ prompt }}"}' } : undefined,
        stream: protocol === 'sse' ? { path: '', eventField: 'data' } : undefined,
        websocket: protocol === 'websocket' ? { path: '', messageTemplate: '{"message":"{{ prompt }}"}', responseMessageField: 'message' } : undefined,
        response: { type: 'json-path', path: '$.output', fallbackPath: '$.choices.0.message.content' },
      },
    },
  }
}

export function applyTemplate(config: ConnectorConfig, protocol: ConnectorProtocol) {
  const next = defaultConnectorConfig(protocol, config.connector_type)
  return { ...config, uri: next.uri, params: next.params }
}

export function endpointToConfig(endpoint: ConnectorEndpointItem): ConnectorConfig {
  const params = normalizeParams(endpoint.params)
  const meta = readMeta()[endpoint.id]
  return {
    id: endpoint.id,
    name: endpoint.name,
    description: '',
    connector_type: endpoint.connector_type,
    uri: endpoint.uri,
    token: endpoint.token || '',
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

function normalizeParams(params: Record<string, unknown>) {
  if (params.connector_config) return params as ConnectorConfig['params']
  return defaultConnectorConfig('http').params
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
