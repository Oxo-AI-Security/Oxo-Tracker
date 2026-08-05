import { beforeAll, describe, expect, it } from 'vitest'
import { CONFIGURABLE_CONNECTOR, defaultConnectorConfig, endpointToConfig, migrateConnectorProtocol } from './connectorService'
import type { ConnectorEndpointItem } from '../types/connector'

beforeAll(() => {
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: {
      localStorage: {
        getItem: () => null,
        setItem: () => undefined,
      },
    },
  })
})

describe('configurable connector request headers', () => {
  it('does not create a separate authentication configuration', () => {
    const config = defaultConnectorConfig('http')

    expect(config.token).toBe('')
    expect(config.params.connector_config).not.toHaveProperty('auth')
  })

  it('migrates a legacy bearer token into request headers when editing', () => {
    const endpoint: ConnectorEndpointItem = {
      id: 'legacy-endpoint',
      name: 'Legacy endpoint',
      connector_type: CONFIGURABLE_CONNECTOR,
      uri: 'https://example.test/chat',
      token: 'legacy-secret',
      model: '',
      max_calls_per_second: 1,
      max_concurrency: 1,
      params: {
        timeout: 30,
        connector_config: {
          transport: 'http',
          auth: { type: 'bearer' },
          request: {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            bodyType: 'json',
            bodyTemplate: '{"message":"{{ prompt }}"}',
          },
          response: { type: 'json-path', path: '$.output' },
        },
      },
    }

    const config = endpointToConfig(endpoint)

    expect(config.token).toBe('')
    expect(config.params.connector_config).not.toHaveProperty('auth')
    expect(config.params.connector_config.request?.headers.Authorization).toBe('Bearer legacy-secret')
  })

  it('restores the saved response sample and selected output marker when editing', () => {
    const sampleResponse = '{\n  "blocked": false,\n  "response": "{{ output }}"\n}'
    const endpoint: ConnectorEndpointItem = {
      id: 'mapped-endpoint',
      name: 'Mapped endpoint',
      connector_type: CONFIGURABLE_CONNECTOR,
      uri: 'https://example.test/chat',
      token: '',
      model: '',
      max_calls_per_second: 1,
      max_concurrency: 1,
      params: {
        timeout: 30,
        connector_config: {
          transport: 'http',
          request: {
            method: 'POST',
            path: '',
            headers: { 'content-type': 'application/json' },
            bodyType: 'json',
            bodyTemplate: '{"message":"{{ prompt }}"}',
          },
          response: { type: 'json-path', path: '$.response', sampleResponse },
        },
      },
    }

    const config = endpointToConfig(endpoint)

    expect(config.params.connector_config.response.path).toBe('$.response')
    expect(config.params.connector_config.response.sampleResponse).toBe(sampleResponse)
  })

  it('migrates a legacy selected response fragment to its JSON path', () => {
    const sampleResponse =
      '{"history_metadata":{"title":"Initial Greeting"}}\n' +
      '{"choices":[{"messages":[{"content":"{{ output }}"}]}]}'
    const endpoint: ConnectorEndpointItem = {
      id: 'legacy-mapped-endpoint',
      name: 'Legacy mapped endpoint',
      connector_type: CONFIGURABLE_CONNECTOR,
      uri: 'https://example.test/chat',
      token: '',
      model: '',
      max_calls_per_second: 1,
      max_concurrency: 1,
      params: {
        timeout: 30,
        connector_config: {
          transport: 'http',
          request: {
            method: 'POST',
            path: '',
            headers: { 'content-type': 'application/json' },
            bodyType: 'json',
            bodyTemplate: '{"message":"{{ prompt }}"}',
          },
          response: {
            type: 'text-fragment',
            path: '',
            selectedText: 'Old answer',
            sampleResponse,
          },
        },
      },
    }

    const config = endpointToConfig(endpoint)

    expect(config.params.connector_config.response.type).toBe('json-path')
    expect(config.params.connector_config.response.path).toBe('$.choices.0.messages.0.content')
  })

  it('preserves manually entered request data when switching an HTTP response to SSE', () => {
    const config = defaultConnectorConfig('http')
    config.uri = 'https://example.test/events'
    config.params.connector_config.request = {
      method: 'POST',
      path: 'stream',
      headers: { Authorization: 'Bearer secret', Accept: 'text/event-stream' },
      queryParams: { tenant: 'oxo' },
      bodyType: 'multipart',
      formFields: { requirement: '{{ prompt }}' },
      bodyTemplate: '',
    }

    const migrated = migrateConnectorProtocol(config, 'sse')

    expect(migrated.params.connector_config.transport).toBe('sse')
    expect(migrated.params.connector_config.request).toBeUndefined()
    expect(migrated.params.connector_config.stream).toMatchObject({
      method: 'POST',
      path: 'stream',
      headers: { Authorization: 'Bearer secret', Accept: 'text/event-stream' },
      queryParams: { tenant: 'oxo' },
      bodyType: 'multipart',
      formFields: { requirement: '{{ prompt }}' },
    })
  })

  it('converts the URL and message body when a WebSocket endpoint is detected', () => {
    const config = defaultConnectorConfig('http')
    config.uri = 'https://example.test/socket'
    config.params.connector_config.request!.bodyTemplate = '{"message":"{{ prompt }}","mode":"safe"}'

    const migrated = migrateConnectorProtocol(config, 'websocket')

    expect(migrated.uri).toBe('wss://example.test/socket')
    expect(migrated.params.connector_config.websocket?.messageTemplate).toContain('"mode":"safe"')
  })
})
