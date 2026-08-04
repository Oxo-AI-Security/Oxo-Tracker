import { describe, expect, it } from 'vitest'
import {
  compareVersions,
  downloadInstallAndRelaunch,
  hasPendingCachedUpdate,
  shouldCheckForUpdateOnStartup,
  shouldShowUpdateNotice,
  type CachedUpdateState,
} from './updater'
import type { DownloadEvent, Update } from '@tauri-apps/plugin-updater'

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

  it('downloads fully, stops the backend, and only then starts the installer', async () => {
    const calls: string[] = []
    const progress: number[] = []
    const update = {
      download: async (onEvent: (event: DownloadEvent) => void) => {
        calls.push('download')
        onEvent({ event: 'Started', data: { contentLength: 10 } })
        onEvent({ event: 'Progress', data: { chunkLength: 10 } })
        onEvent({ event: 'Finished' })
      },
      install: async () => {
        calls.push('install')
      },
    } as unknown as Update

    await downloadInstallAndRelaunch(
      update,
      (value) => progress.push(value.percent ?? -1),
      {
        prepareForInstall: async () => {
          calls.push('prepare')
        },
        relaunch: async () => {
          calls.push('relaunch')
        },
      },
    )

    expect(calls).toEqual(['download', 'prepare', 'install', 'relaunch'])
    expect(progress).toEqual([0, 100, 100])
  })

  it('does not launch the installer when the backend cannot be stopped', async () => {
    const calls: string[] = []
    const update = {
      download: async () => {
        calls.push('download')
      },
      install: async () => {
        calls.push('install')
      },
    } as unknown as Update

    await expect(downloadInstallAndRelaunch(
      update,
      () => undefined,
      {
        prepareForInstall: async () => {
          calls.push('prepare')
          throw new Error('backend is still running')
        },
        relaunch: async () => {
          calls.push('relaunch')
        },
      },
    )).rejects.toThrow('backend is still running')

    expect(calls).toEqual(['download', 'prepare'])
  })
})
