import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { darkTheme } from 'naive-ui'
import { moonshotApi } from '../api/moonshot'
import { setI18nLocale } from '../i18n'
import type { AISettings, AppSettings } from '../types/moonshot'

const LOCALE_STORAGE_KEY = 'oxo-tracker-locale'

function readStoredLocale(): AppSettings['locale'] | null {
  if (typeof window === 'undefined') return null
  const value = window.localStorage.getItem(LOCALE_STORAGE_KEY)
  return value === 'en-US' || value === 'zh-CN' ? value : null
}

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<AppSettings['theme']>('light')
  const locale = ref<AppSettings['locale']>(readStoredLocale() || 'en-US')
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

  async function loadSettings() {
    loading.value = true
    try {
      const settings = await moonshotApi.getSettings()
      applyTheme(settings.theme)
      applyLocale(settings.locale || readStoredLocale() || 'en-US')
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

  return {
    theme,
    locale,
    ai,
    loading,
    naiveTheme,
    loadSettings,
    setTheme,
    setLocale,
  }
})
