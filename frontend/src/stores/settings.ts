import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { darkTheme } from 'naive-ui'
import { moonshotApi } from '../api/moonshot'
import { isDesktopRuntime } from '../desktop/bootstrap'
import { setI18nLocale } from '../i18n'
import type { AISettings, AppSettings, UiScale } from '../types/moonshot'

const LOCALE_STORAGE_KEY = 'oxo-tracker-locale'
const UI_SCALE_STORAGE_KEY = 'oxo-tracker-ui-scale'
const UI_SCALE_OPTIONS: UiScale[] = [80, 90, 100, 110]

function readStoredLocale(): AppSettings['locale'] | null {
  if (typeof window === 'undefined') return null
  const value = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  return value === 'en-US' || value === 'zh-CN' ? value : null
}

function readStoredUiScale(): UiScale | null {
  if (typeof window === 'undefined') return null
  const value = Number(window.localStorage.getItem(UI_SCALE_STORAGE_KEY))
  return UI_SCALE_OPTIONS.includes(value as UiScale) ? (value as UiScale) : null
}

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<AppSettings['theme']>('light')
  const locale = ref<AppSettings['locale']>(readStoredLocale() || 'en-US')
  const uiScale = ref<UiScale>(readStoredUiScale() || 100)
  const ai = ref<AISettings | null>(null)
  const loading = ref(false)

  const naiveTheme = computed(() => (theme.value === 'dark' ? darkTheme : null))

  function applyTheme(value: AppSettings['theme']) {
    theme.value = value
    document.documentElement.dataset.theme = value
  }

  function applyLocale(value: AppSettings['locale']) {
    locale.value = value
    setI18nLocale(value)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, value)
    }
  }

  function applyBrowserUiScale(value: UiScale) {
    if (typeof document === 'undefined') return
    const canvasScale = 100 / value
    const canvasWidth = `${canvasScale * 100}vw`
    const canvasHeight = `${canvasScale * 100}vh`
    document.documentElement.style.setProperty('zoom', String(value / 100))
    document.documentElement.style.setProperty('width', `${canvasScale * 100}%`)
    document.documentElement.style.setProperty('height', canvasHeight)
    document.documentElement.style.setProperty('--oxo-ui-viewport-width', canvasWidth)
    document.documentElement.style.setProperty('--oxo-ui-viewport-height', canvasHeight)
    document.body.style.setProperty('width', canvasWidth)
    document.body.style.setProperty('height', canvasHeight)
  }

  function resetBrowserUiScale() {
    if (typeof document === 'undefined') return
    document.documentElement.style.removeProperty('zoom')
    document.documentElement.style.removeProperty('width')
    document.documentElement.style.removeProperty('height')
    document.documentElement.style.setProperty('--oxo-ui-viewport-width', '100vw')
    document.documentElement.style.setProperty('--oxo-ui-viewport-height', '100vh')
    document.body.style.removeProperty('width')
    document.body.style.removeProperty('height')
  }

  async function applyUiScale(value: UiScale) {
    uiScale.value = value
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.uiScale = String(value)
    }
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(UI_SCALE_STORAGE_KEY, String(value))
    }
    if (!isDesktopRuntime()) {
      applyBrowserUiScale(value)
      return
    }
    try {
      const { getCurrentWebview } = await import('@tauri-apps/api/webview')
      await getCurrentWebview().setZoom(value / 100)
      resetBrowserUiScale()
    } catch {
      applyBrowserUiScale(value)
    }
  }

  void applyUiScale(uiScale.value)

  async function loadSettings() {
    loading.value = true
    try {
      const settings = await moonshotApi.getSettings()
      applyTheme(settings.theme)
      applyLocale(settings.locale || readStoredLocale() || 'en-US')
      await applyUiScale(settings.uiScale || readStoredUiScale() || 100)
      ai.value = settings.ai
    } finally {
      loading.value = false
    }
  }

  async function setTheme(value: AppSettings['theme']) {
    applyTheme(value)
    const settings = await moonshotApi.updateSettings({ theme: value })
    applyTheme(settings.theme)
    ai.value = settings.ai
  }

  async function setLocale(value: AppSettings['locale']) {
    const previousLocale = locale.value
    applyLocale(value)
    try {
      const settings = await moonshotApi.updateSettings({ locale: value })
      applyTheme(settings.theme)
      applyLocale(settings.locale || value)
      ai.value = settings.ai
    } catch (error) {
      applyLocale(previousLocale)
      throw error
    }
  }

  async function setUiScale(value: UiScale) {
    const previousScale = uiScale.value
    await applyUiScale(value)
    try {
      const settings = await moonshotApi.updateSettings({ uiScale: value })
      applyTheme(settings.theme)
      applyLocale(settings.locale || locale.value)
      await applyUiScale(settings.uiScale || value)
      ai.value = settings.ai
    } catch (error) {
      await applyUiScale(previousScale)
      throw error
    }
  }

  return {
    theme,
    locale,
    uiScale,
    ai,
    loading,
    naiveTheme,
    loadSettings,
    setTheme,
    setLocale,
    setUiScale,
  }
})
