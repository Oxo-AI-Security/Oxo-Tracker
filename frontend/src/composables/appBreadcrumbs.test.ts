import { describe, expect, it } from 'vitest'
import { matchesAppBreadcrumbOverride, type AppBreadcrumbOverride } from './appBreadcrumbs'

describe('app breadcrumb override scope', () => {
  const agentsOverride: AppBreadcrumbOverride = {
    owner: 'agents-workbench',
    breadcrumbs: [{ label: 'Agents' }],
    pathPrefix: '/agents',
  }

  it('uses the workbench override on agent routes', () => {
    expect(matchesAppBreadcrumbOverride(agentsOverride, '/agents')).toBe(true)
    expect(matchesAppBreadcrumbOverride(agentsOverride, '/agents/connectors')).toBe(true)
  })

  it('does not leak the agent breadcrumb onto history or benchmark routes', () => {
    expect(matchesAppBreadcrumbOverride(agentsOverride, '/history')).toBe(false)
    expect(matchesAppBreadcrumbOverride(agentsOverride, '/benchmark')).toBe(false)
  })
})
