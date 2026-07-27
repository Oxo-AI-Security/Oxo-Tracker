import { describe, expect, it } from 'vitest'
import { parseCompactExecutorTechniques } from './executorSkillMarkdown'

describe('parseCompactExecutorTechniques', () => {
  it('parses the fixed compact format in display order', () => {
    const body = [
      '## Purpose',
      'Test a behavior.',
      '',
      '## Techniques',
      '',
      '### safe-baseline',
      'Name: Safe baseline',
      'Stage: baseline',
      'Summary: Establish a baseline.',
      '',
      '### focused-follow-up',
      '- Name: Focused follow-up',
      '- Stage: exploration',
      '- Summary: Change one variable.',
    ].join('\n')

    expect(parseCompactExecutorTechniques(body)).toEqual([
      {
        technique_id: 'safe-baseline',
        name: 'Safe baseline',
        stage: 'baseline',
        summary: 'Establish a baseline.',
      },
      {
        technique_id: 'focused-follow-up',
        name: 'Focused follow-up',
        stage: 'exploration',
        summary: 'Change one variable.',
      },
    ])
  })

  it('leaves legacy Technique Catalog content to existing metadata', () => {
    expect(
      parseCompactExecutorTechniques(
        '## Technique Catalog\n\n### safe-baseline\n\nLegacy detail.',
      ),
    ).toEqual([])
  })

  it('ignores an incomplete technique block', () => {
    expect(
      parseCompactExecutorTechniques(
        '## Techniques\n\n### safe-baseline\nName: Safe baseline\nStage: baseline',
      ),
    ).toEqual([])
  })
})
