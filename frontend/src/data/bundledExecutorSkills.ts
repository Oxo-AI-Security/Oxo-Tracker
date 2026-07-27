import type {
  ExecutorSkill,
  ExecutorSkillCatalogItem,
  ExecutorSkillMetadata,
} from '../api/taskAgents'

import indirectInstructionBoundary from '../../../app/executor_skills/indirect-instruction-boundary/SKILL.md?raw'
import modelFingerprintTriangulation from '../../../app/executor_skills/model-fingerprint-triangulation/SKILL.md?raw'
import progressiveContextProbing from '../../../app/executor_skills/progressive-context-probing/SKILL.md?raw'
import promptVariationTesting from '../../../app/executor_skills/prompt-variation-testing/SKILL.md?raw'
import ragRetrievalBoundaryMapping from '../../../app/executor_skills/rag-retrieval-boundary-mapping/SKILL.md?raw'
import refusalDifferentialValidation from '../../../app/executor_skills/refusal-differential-validation/SKILL.md?raw'
import toolCapabilityBoundaryMapping from '../../../app/executor_skills/tool-capability-boundary-mapping/SKILL.md?raw'
import workflowIntegrityDifferential from '../../../app/executor_skills/workflow-integrity-differential/SKILL.md?raw'

const rawSkills = [
  indirectInstructionBoundary,
  modelFingerprintTriangulation,
  progressiveContextProbing,
  promptVariationTesting,
  ragRetrievalBoundaryMapping,
  refusalDifferentialValidation,
  toolCapabilityBoundaryMapping,
  workflowIntegrityDifferential,
]

function unquote(value: string) {
  const trimmed = value.trim()
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1)
  }
  return trimmed
}

function field(source: string, name: string, indent = '') {
  const match = source.match(
    new RegExp(`^${indent}${name}:\\s*(.+?)\\s*$`, 'm'),
  )
  return match ? unquote(match[1] || '') : ''
}

function stringList(source: string, name: string) {
  const start = source.search(new RegExp(`^  ${name}:`, 'm'))
  if (start < 0) return []
  const rest = source.slice(start).split('\n')
  if ((rest[0] || '').trim().endsWith('[]')) return []
  const values: string[] = []
  for (const line of rest.slice(1)) {
    if (/^  [a-z_]+:/.test(line)) break
    const match = line.match(/^    -\s+(.+?)\s*$/)
    if (match?.[1]) values.push(unquote(match[1]))
  }
  return values
}

function techniques(source: string): ExecutorSkillMetadata['techniques'] {
  const start = source.search(/^  techniques:\s*$/m)
  const end = source.search(/^  composable_with:/m)
  if (start < 0 || end < 0 || end <= start) return []
  const block = source.slice(start, end)
  return block
    .split(/\n(?=    - technique_id:)/)
    .slice(1)
    .map((item) => ({
      technique_id: field(item, 'technique_id', '    - '),
      name: field(item, 'name', '      '),
      summary: field(item, 'summary', '      '),
      stage: field(item, 'stage', '      '),
    }))
    .filter((item) => item.technique_id)
}

function parseBundledSkill(raw: string): ExecutorSkill {
  const normalized = raw.replace(/\r\n/g, '\n')
  const frontmatterEnd = normalized.indexOf('\n---', 4)
  if (!normalized.startsWith('---\n') || frontmatterEnd < 0) {
    throw new Error('Invalid bundled Executor Skill frontmatter')
  }
  const frontmatter = normalized.slice(4, frontmatterEnd)
  const body = normalized.slice(frontmatterEnd + 4).replace(/^\n+/, '')
  const metadata: ExecutorSkillMetadata = {
    version: field(frontmatter, 'version', '  '),
    category: field(frontmatter, 'category', '  '),
    stage: field(frontmatter, 'stage', '  '),
    risk_level: 'low',
    skill_type:
      field(frontmatter, 'skill_type', '  ') === 'AUXILIARY'
        ? 'AUXILIARY'
        : 'DOMAIN',
    techniques: techniques(frontmatter),
    composable_with: stringList(frontmatter, 'composable_with'),
    conflicts_with: stringList(frontmatter, 'conflicts_with'),
    allow_primary: field(frontmatter, 'allow_primary', '  ') === 'true',
    allow_supporting: field(frontmatter, 'allow_supporting', '  ') === 'true',
  }
  return {
    name: field(frontmatter, 'name'),
    description: field(frontmatter, 'description'),
    compatibility: field(frontmatter, 'compatibility'),
    metadata,
    enabled: field(frontmatter, 'enabled') !== 'false',
    body,
  }
}

const bundledSkills = rawSkills
  .map(parseBundledSkill)
  .sort((left, right) => left.name.localeCompare(right.name))

export function listBundledExecutorSkills(): ExecutorSkillCatalogItem[] {
  return bundledSkills.map(({ body: _body, ...skill }) => skill)
}

export function getBundledExecutorSkill(skillId: string) {
  const skill = bundledSkills.find((item) => item.name === skillId)
  return skill ? structuredClone(skill) : null
}
