import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { darkTheme } from 'naive-ui'
import { moonshotApi } from '../api/moonshot'
import type { AISettings, AppSettings } from '../types/moonshot'

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<AppSettings['theme']>('light')
  const ai = ref<AISettings | null>(null)
  const loading = ref(false)

  const naiveTheme = computed(() => (theme.value === 'dark' ? darkTheme : null))

  function applyTheme(value: AppSettings['theme']) {
    theme.value = value
    document.documentElement.dataset.theme = value
  }

  async function loadSettings() {
    loading.value = true
    try {
      const settings = await moonshotApi.getSettings()
      applyTheme(settings.theme)
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

  return {
    theme,
    ai,
    loading,
    naiveTheme,
    loadSettings,
    setTheme,
  }
})
