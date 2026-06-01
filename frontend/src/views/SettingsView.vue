<template>
  <div class="settings-page-shell">
    <section class="settings-page-head">
      <p class="eyebrow">System &gt; Settings</p>
      <h2>Settings</h2>
    </section>

    <div class="settings-row-list">
      <article class="settings-row-card">
        <div>
          <strong>Theme settings</strong>
          <span>Choose the interface color mode for this workspace.</span>
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

      <article class="settings-row-card">
        <div>
          <strong>Appearance mode</strong>
          <span>Current UI theme applied across Oxo Tracker.</span>
        </div>
        <n-tag round type="info">{{ settings.theme }}</n-tag>
      </article>

      <article class="settings-row-card">
        <div>
          <strong>Backend status</strong>
          <span>API health and indexed asset inventory.</span>
        </div>
        <div class="settings-status">
          <n-tag round :type="store.health === 'ok' ? 'success' : 'warning'">{{ store.health }}</n-tag>
          <span>{{ store.totalAssets }} indexed assets</span>
          <n-button secondary round size="small" @click="store.loadOverview">
            <template #icon><n-icon><RefreshOutline /></n-icon></template>
            Refresh
          </n-button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RefreshOutline } from '@vicons/ionicons5'
import { useMoonshotStore } from '../stores/moonshot'
import { useSettingsStore } from '../stores/settings'

const store = useMoonshotStore()
const settings = useSettingsStore()
</script>
