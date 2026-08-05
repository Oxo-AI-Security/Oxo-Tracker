import { describe, expect, it } from 'vitest'
import { extractResponse, parseJsonDocuments } from './responseExtractor'

describe('responseExtractor', () => {
  it('parses concatenated JSON documents', () => {
    const documents = parseJsonDocuments(
      '{"history_metadata":{"title":"Initial Greeting"}}\n' +
      '{"choices":[{"messages":[{"content":"Final answer"}]}]}',
    )

    expect(documents).toHaveLength(2)
  })

  it('extracts the configured response path from the last JSON document', () => {
    const raw =
      '{"history_metadata":{"title":"Initial Greeting"}}\n' +
      '{"choices":[{"messages":[{"content":"Final answer"}]}]}'

    expect(extractResponse(raw, {
      type: 'json-path',
      path: '$.choices.0.messages.0.content',
    })).toBe('Final answer')
  })

  it('uses the output marker in a legacy text fragment sample as a JSON path', () => {
    const sampleResponse =
      '{"history_metadata":{"title":"Initial Greeting"}}\n' +
      '{"choices":[{"messages":[{"content":"{{ output }}"}]}]}'
    const raw =
      '{"history_metadata":{"title":"Initial Greeting"}}\n' +
      '{"choices":[{"messages":[{"content":"Current answer"}]}]}'

    expect(extractResponse(raw, {
      type: 'text-fragment',
      path: '',
      selectedText: 'Old answer',
      sampleResponse,
    })).toBe('Current answer')
  })
})
