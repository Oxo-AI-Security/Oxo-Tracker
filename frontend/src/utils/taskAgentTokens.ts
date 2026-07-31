export interface TaskAgentTokenTurn {
  round_key?: string
  request?: string | null
  prepared_request?: string | null
  response?: string | null
}

export interface TaskAgentTokenEstimate {
  inputTokens: number
  outputTokens: number
  totalTokens: number
}

export function estimateTextTokens(value: string | null | undefined): number {
  return Array.from(String(value || '')).length
}

export function estimateTaskAgentTargetTokens(
  turns: TaskAgentTokenTurn[] | null | undefined,
): TaskAgentTokenEstimate {
  const seenRounds = new Set<string>()
  let inputTokens = 0
  let outputTokens = 0

  for (const [index, turn] of (turns || []).entries()) {
    const roundKey = String(turn.round_key || `turn-${index}`)
    if (seenRounds.has(roundKey)) continue
    seenRounds.add(roundKey)

    inputTokens += estimateTextTokens(turn.prepared_request || turn.request)
    outputTokens += estimateTextTokens(turn.response)
  }

  return {
    inputTokens,
    outputTokens,
    totalTokens: inputTokens + outputTokens,
  }
}
