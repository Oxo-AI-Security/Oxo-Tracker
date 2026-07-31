import { describe, expect, it } from 'vitest'

import {
  estimateTaskAgentTargetTokens,
  estimateTextTokens,
} from './taskAgentTokens'

describe('task agent target token estimates', () => {
  it('uses one token per Unicode character', () => {
    expect(estimateTextTokens('系统提示')).toBe(4)
    expect(estimateTextTokens('A B')).toBe(3)
    expect(estimateTextTokens('🙂')).toBe(1)
  })

  it('counts the final prepared request and target response', () => {
    expect(
      estimateTaskAgentTargetTokens([
        {
          round_key: 'round-1',
          request: 'raw',
          prepared_request: '最终输入',
          response: '目标回复',
        },
      ]),
    ).toEqual({
      inputTokens: 4,
      outputTokens: 4,
      totalTokens: 8,
    })
  })

  it('does not count a repeated committed round twice', () => {
    const turn = {
      round_key: 'round-1',
      prepared_request: 'abc',
      response: 'de',
    }
    expect(estimateTaskAgentTargetTokens([turn, turn])).toEqual({
      inputTokens: 3,
      outputTokens: 2,
      totalTokens: 5,
    })
  })
})
