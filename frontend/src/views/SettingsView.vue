<template>
  <div class="settings-page-shell">
    <div class="settings-row-list">
      <RouterLink to="/settings/ai" class="settings-row-card settings-row-card--link">
        <div class="settings-row-main">
          <span class="settings-row-icon settings-row-icon--ai">
            <n-icon size="22"><SparklesOutline /></n-icon>
          </span>
          <div>
            <strong>AI settings</strong>
            <span>Choose the single LLM provider and model used by this workspace.</span>
          </div>
        </div>
        <div class="settings-row-action">
          <span v-if="settings.ai" class="settings-active-model">
            {{ activeProviderLabel }} · {{ activeModel }}
          </span>
          <n-icon size="20"><ChevronForwardOutline /></n-icon>
        </div>
      </RouterLink>

      <article class="settings-row-card">
        <div class="settings-row-main">
          <span class="settings-row-icon">
            <n-icon size="22"><ColorPaletteOutline /></n-icon>
          </span>
          <div>
            <strong>Theme settings</strong>
            <span>Choose how Oxo Tracker looks across this workspace.</span>
          </div>
        </div>
        <div class="theme-toggle settings-theme-toggle">
          <button type="button" :class="{ active: settings.theme === 'light' }" @click="settings.setTheme('light')">
            Light
          </button>
          <button type="button" :class="{ active: settings.theme === 'dark' }" @click="settings.setTheme('dark')">
            Dark
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronForwardOutline, ColorPaletteOutline, SparklesOutline } from '@vicons/ionicons5'
import { useSettingsStore } from '../stores/settings'

const settings = useSettingsStore()
const activeProviderLabel = computed(() => {
  const id = settings.ai?.activeProvider
  if (!id) return 'Not configured'
  return settings.ai?.catalog[id]?.label || 'Not configured'
})
const activeModel = computed(() => {
  const id = settings.ai?.activeProvider
  if (!id) return 'Select a model'
  return settings.ai?.providers[id]?.model || 'Select a model'
})
</script>
