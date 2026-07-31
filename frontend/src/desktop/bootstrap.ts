import { configureApiRuntime } from '../api/http'

interface DesktopBootstrap {
  apiBaseUrl: string
  token: string
}

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown
  }
}

export function isDesktopRuntime() {
  return typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__)
}

export async function initializeDesktopRuntime() {
  if (!isDesktopRuntime()) return
  document.documentElement.classList.add('tauri-window')
  const { invoke } = await import('@tauri-apps/api/core')
  const runtime = await invoke<DesktopBootstrap>('desktop_bootstrap')
  configureApiRuntime(runtime.apiBaseUrl, runtime.token)
}
