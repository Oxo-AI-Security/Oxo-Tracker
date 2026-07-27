export function isRunnerEnvelopeWithoutAssistantResponse(value: unknown) {
  let parsed = value
  if (typeof parsed === 'string') {
    const trimmed = parsed.trim()
    if (!trimmed.startsWith('{')) return false
    try {
      parsed = JSON.parse(trimmed)
    } catch {
      return false
    }
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return false
  const record = parsed as Record<string, unknown>
  const currentChats = record.current_chats
  if (!currentChats || typeof currentChats !== 'object' || Array.isArray(currentChats)) {
    return false
  }
  let foundChat = false
  for (const group of Object.values(currentChats as Record<string, unknown>)) {
    if (!Array.isArray(group)) continue
    for (const item of group) {
      if (!item || typeof item !== 'object' || Array.isArray(item)) continue
      foundChat = true
      const chat = item as Record<string, unknown>
      if (
        ['predicted_result', 'response', 'answer', 'content', 'output', 'result']
          .some((key) => String(chat[key] || '').trim())
      ) {
        return false
      }
    }
  }
  return foundChat
}
