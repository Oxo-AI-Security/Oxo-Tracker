export type ConnectorProtocol = 'http' | 'sse' | 'websocket'
export type ConnectorSource = 'built-in' | 'user-created'
export type AuthType = 'none' | 'bearer' | 'api-key' | 'cookie' | 'basic'

export interface ConnectorOwner {
  id: string
  name: string
  email?: string
}

export interface CurrentUser extends ConnectorOwner {}

export interface AuthConfig {
  type: AuthType
  secretRef?: string
  headerName?: string
  usernameRef?: string
  passwordRef?: string
}

export interface HttpRequestConfig {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH'
  path: string
  headers: Record<string, string>
  bodyTemplate: string
}

export interface SseStreamConfig {
  path: string
  eventField: string
  dataPrefix?: string
}

export interface WebSocketConfig {
  path: string
  messageTemplate: string
  responseMessageField: string
}

export interface ResponseExtractConfig {
  type: 'json-path' | 'text' | 'event-data'
  path: string
  fallbackPath?: string
}

export interface ConnectorConfig {
  id?: string
  name: string
  description?: string
  connector_type: string
  uri: string
  token: string
  model: string
  source: ConnectorSource
  ownerId: string
  ownerName: string
  max_calls_per_second: number
  max_concurrency: number
  params: {
    timeout: number
    connector_config: {
      transport: ConnectorProtocol
      auth: AuthConfig
      request?: HttpRequestConfig
      stream?: SseStreamConfig
      websocket?: WebSocketConfig
      response: ResponseExtractConfig
    }
  }
}

export interface ConnectorListItem {
  id: string
  name: string
  description?: string
  protocol: ConnectorProtocol
  uri: string
  source: ConnectorSource
  ownerId: string
  ownerName: string
  createdAt: string
  updatedAt: string
  editable: boolean
  deletable: boolean
  config: ConnectorConfig
  endpoints?: ConnectorEndpointItem[]
  endpointCount?: number
}

export interface ConnectorEndpointItem {
  id: string
  name: string
  connector_type: string
  uri: string
  token: string
  max_calls_per_second: number
  max_concurrency: number
  model: string
  params: Record<string, unknown>
  created_date?: string
}

export interface ConnectorTestResult {
  status: 'success' | 'error'
  duration: number
  requestPreview: string
  rawResponse: string
  extractedResponse: string
  error?: string
}
