import type { ExecutorSkillMetadata } from '../api/taskAgents'

export type ExecutorTechnique = ExecutorSkillMetadata['techniques'][number]

export function parseCompactExecutorTechniques(body: string): ExecutorTechnique[] {
  const techniques: ExecutorTechnique[] = []
  let inTechniques = false
  let techniqueId = ''
  let fields: Partial<Omit<ExecutorTechnique, 'technique_id'>> = {}

  const finishTechnique = () => {
    if (techniqueId && fields.name && fields.stage && fields.summary) {
      techniques.push({
        technique_id: techniqueId,
        name: fields.name,
        stage: fields.stage,
        summary: fields.summary,
      })
    }
    techniqueId = ''
    fields = {}
  }

  for (const line of body.split(/\r?\n/)) {
    if (/^##\s+Techniques\s*$/i.test(line)) {
      inTechniques = true
      continue
    }
    if (!inTechniques) continue
    if (/^##\s+/.test(line)) break

    const heading = line.match(/^###\s+([a-z0-9][a-z0-9-]{1,79})\s*$/i)
    if (heading) {
      finishTechnique()
      techniqueId = heading[1] ?? ''
      continue
    }
    if (!techniqueId) continue

    const field = line.match(/^\s*(?:-\s*)?(Name|Stage|Summary):\s*(.+?)\s*$/i)
    if (!field?.[1] || !field[2]) continue
    fields[field[1].toLowerCase() as 'name' | 'stage' | 'summary'] = field[2].trim()
  }
  finishTechnique()
  return techniques
}
