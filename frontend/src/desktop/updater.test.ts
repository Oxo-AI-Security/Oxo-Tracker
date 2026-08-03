import { describe, expect, it } from 'vitest'
import {
  compareVersions,
  hasPendingCachedUpdate,
  shouldCheckForUpdateOnStartup,
  shouldShowUpdateNotice,
  type CachedUpdateState,
} from './updater'

const cache = (latestVersion: string): CachedUpdateState => ({
  checkedAt: '2026-08-02T12:00:00Z',
  latestVersion,
  notes: '',
  pubDate: null,
})

describe('desktop updater state', () => {
  it('compares stable and prerelease semantic versions', () => {
    expect(compareVersions('0.2.0', '0.1.9')).toBe(1)
    expect(compareVersions('v1.0.0', '1.0.0')).toBe(0)
    expect(compareVersions('1.0.0-beta.2', '1.0.0-beta.11')).toBe(-1)
    expect(compareVersions('1.0.0', '1.0.0-rc.1')).toBe(1)
  })

  it('does not query on startup while a previously detected update is pending', () => {
    expect(hasPendingCachedUpdate(cache('0.2.0'), '0.1.0')).toBe(true)
    expect(shouldCheckForUpdateOnStartup(cache('0.2.0'), '0.1.0')).toBe(false)
  })

  it('queries on startup when no newer version is cached', () => {
    expect(shouldCheckForUpdateOnStartup(null, '0.1.0')).toBe(true)
    expect(shouldCheckForUpdateOnStartup(cache('0.1.0'), '0.1.0')).toBe(true)
    expect(shouldCheckForUpdateOnStartup(cache('0.0.9'), '0.1.0')).toBe(true)
  })

  it('shows an update notice once per application session', () => {
    expect(shouldShowUpdateNotice(true, false)).toBe(true)
    expect(shouldShowUpdateNotice(true, true)).toBe(false)
    expect(shouldShowUpdateNotice(false, false)).toBe(false)
    expect(shouldShowUpdateNotice(true, false)).toBe(true)
  })
})
