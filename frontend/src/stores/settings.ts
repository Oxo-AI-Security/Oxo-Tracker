import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { darkTheme } from 'naive-ui'
import { moonshotApi } from '../api/moonshot'
import type { AppSettings } from '../types/moonshot'

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<AppSettings['theme']>('light')
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
    } finally {
      loading.value = false
    }
  }

  async function setTheme(value: AppSettings['theme']) {
    applyTheme(value)
    const settings = await moonshotApi.updateSettings({ theme: value })
    applyTheme(settings.theme)
  }

  return {
    theme,
    loading,
    naiveTheme,
    loadSettings,
    setTheme,
  }
})
