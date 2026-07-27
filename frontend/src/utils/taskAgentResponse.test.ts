import { describe, expect, it } from 'vitest'
import { isRunnerEnvelopeWithoutAssistantResponse } from './taskAgentResponse'

describe('Task Agent target response display', () => {
  it('recognizes a completed runner envelope with no assistant result', () => {
    const envelope = {
      current_runner_id: 'runner',
      current_chats: {
        session: [
          {
            prompt: 'hello',
            predicted_result: '',
            duration: '30.03',
          },
        ],
      },
      current_status: 'COMPLETED',
    }

    expect(isRunnerEnvelopeWithoutAssistantResponse(envelope)).toBe(true)
    expect(isRunnerEnvelopeWithoutAssistantResponse(JSON.stringify(envelope))).toBe(true)
  })

  it('keeps a runner envelope that contains a real assistant result', () => {
    expect(
      isRunnerEnvelopeWithoutAssistantResponse({
        current_chats: {
          session: [{ predicted_result: 'assistant answer' }],
        },
      }),
    ).toBe(false)
  })
})
