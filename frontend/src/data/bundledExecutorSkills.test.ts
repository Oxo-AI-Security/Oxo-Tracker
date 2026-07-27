import { describe, expect, it } from 'vitest'

import {
  getBundledExecutorSkill,
  listBundledExecutorSkills,
} from './bundledExecutorSkills'

describe('bundledExecutorSkills', () => {
  it('returns editable copies without mutating the bundled template', () => {
    const skillId = listBundledExecutorSkills()[0]?.name
    expect(skillId).toBeTruthy()

    const first = getBundledExecutorSkill(skillId!)
    expect(first).not.toBeNull()
    first!.name = 'edited-template'
    first!.metadata.techniques[0]!.summary = 'edited summary'

    const second = getBundledExecutorSkill(skillId!)
    expect(second?.name).toBe(skillId)
    expect(second?.metadata.techniques[0]?.summary).not.toBe('edited summary')
  })
})
