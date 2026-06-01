<template>
  <n-config-provider :theme="settings.naiveTheme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-notification-provider placement="top-right">
        <router-view />
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import type { GlobalThemeOverrides } from 'naive-ui'
import { useSettingsStore } from './stores/settings'

const settings = useSettingsStore()

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#47d7ff',
    primaryColorHover: '#2f8dff',
    primaryColorPressed: '#7b5cff',
    borderRadius: '8px',
    bodyColor: '#f4f8ff',
    textColorBase: '#142033',
    textColor1: '#142033',
    textColor2: '#40516c',
    textColor3: '#64748b',
    borderColor: 'rgba(45, 103, 171, 0.16)',
    cardColor: 'rgba(255, 255, 255, 0.72)',
    modalColor: 'rgba(255, 255, 255, 0.96)',
  },
  Card: {
    color: 'rgba(255, 255, 255, 0.76)',
    borderColor: 'rgba(45, 103, 171, 0.16)',
    borderRadius: '8px',
  },
  DataTable: {
    thColor: 'rgba(235, 244, 255, 0.92)',
    tdColor: 'rgba(255, 255, 255, 0.54)',
    borderColor: 'rgba(45, 103, 171, 0.12)',
  },
  Layout: {
    color: 'transparent',
    siderColor: 'transparent',
  },
}

onMounted(() => {
  settings.loadSettings()
})
</script>
