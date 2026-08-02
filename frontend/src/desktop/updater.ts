import type { Update } from '@tauri-apps/plugin-updater'

export const UPDATE_CACHE_KEY = 'oxo-tracker:update-state:v1'

export interface CachedUpdateState {
  checkedAt: string
  latestVersion: string
  notes: string
  pubDate: string | null
}

export interface UpdateDownloadProgress {
  downloadedBytes: number
  totalBytes: number | null
  percent: number | null
  finished: boolean
}

interface ParsedVersion {
  core: [number, number, number]
  prerelease: Array<number | string>
}

function parseVersion(value: string): ParsedVersion | null {
  const match = value.trim().match(/^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/)
  if (!match) return null
  return {
    core: [Number(match[1]), Number(match[2]), Number(match[3])],
    prerelease: match[4]
      ? match[4].split('.').map((part) => (/^\d+$/.test(part) ? Number(part) : part))
      : [],
  }
}

export function compareVersions(left: string, right: string): number {
  const a = parseVersion(left)
  const b = parseVersion(right)
  if (!a || !b) return 0

  for (let index = 0; index < a.core.length; index += 1) {
    if (a.core[index] !== b.core[index]) return a.core[index] > b.core[index] ? 1 : -1
  }
  if (!a.prerelease.length && !b.prerelease.length) return 0
  if (!a.prerelease.length) return 1
  if (!b.prerelease.length) return -1

  const length = Math.max(a.prerelease.length, b.prerelease.length)
  for (let index = 0; index < length; index += 1) {
    const aPart = a.prerelease[index]
    const bPart = b.prerelease[index]
    if (aPart === undefined) return -1
    if (bPart === undefined) return 1
    if (aPart === bPart) continue
    if (typeof aPart === 'number' && typeof bPart === 'string') return -1
    if (typeof aPart === 'string' && typeof bPart === 'number') return 1
    return aPart > bPart ? 1 : -1
  }
  return 0
}

export function hasPendingCachedUpdate(cache: CachedUpdateState | null, currentVersion: string) {
  return Boolean(cache && compareVersions(cache.latestVersion, currentVersion) > 0)
}

export function shouldCheckForUpdateOnStartup(cache: CachedUpdateState | null, currentVersion: string) {
  return !hasPendingCachedUpdate(cache, currentVersion)
}

export function loadCachedUpdateState(storage: Storage = window.localStorage): CachedUpdateState | null {
  try {
    const raw = storage.getItem(UPDATE_CACHE_KEY)
    if (!raw) return null
    const value = JSON.parse(raw) as Partial<CachedUpdateState>
    if (typeof value.checkedAt !== 'string' || typeof value.latestVersion !== 'string') return null
    return {
      checkedAt: value.checkedAt,
      latestVersion: value.latestVersion,
      notes: typeof value.notes === 'string' ? value.notes : '',
      pubDate: typeof value.pubDate === 'string' ? value.pubDate : null,
    }
  } catch {
    return null
  }
}

export function saveCachedUpdateState(
  state: CachedUpdateState,
  storage: Storage = window.localStorage,
) {
  storage.setItem(UPDATE_CACHE_KEY, JSON.stringify(state))
}

export async function checkForDesktopUpdate(): Promise<Update | null> {
  const { check } = await import('@tauri-apps/plugin-updater')
  return check({
    timeout: 15_000,
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache',
    },
  })
}

export async function downloadInstallAndRelaunch(
  update: Update,
  onProgress: (progress: UpdateDownloadProgress) => void,
) {
  let downloadedBytes = 0
  let totalBytes: number | null = null
  await update.downloadAndInstall((event) => {
    if (event.event === 'Started') {
      totalBytes = event.data.contentLength ?? null
    } else if (event.event === 'Progress') {
      downloadedBytes += event.data.chunkLength
    }
    const finished = event.event === 'Finished'
    onProgress({
      downloadedBytes,
      totalBytes,
      percent: totalBytes && totalBytes > 0
        ? Math.min(100, Math.round((downloadedBytes / totalBytes) * 100))
        : null,
      finished,
    })
  })
  const { relaunch } = await import('@tauri-apps/plugin-process')
  await relaunch()
}

