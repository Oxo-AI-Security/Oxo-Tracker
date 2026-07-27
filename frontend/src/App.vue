<template>
  <n-config-provider
    :theme="settings.naiveTheme"
    :theme-overrides="themeOverrides"
    :locale="naiveLocale"
    :date-locale="naiveDateLocale"
  >
    <n-message-provider>
      <n-notification-provider placement="top-right">
        <router-view />
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { dateEnUS, dateZhCN, enUS, zhCN } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { useSettingsStore } from './stores/settings'

const settings = useSettingsStore()
const naiveLocale = computed(() => (settings.locale === 'zh-CN' ? zhCN : enUS))
const naiveDateLocale = computed(() => (settings.locale === 'zh-CN' ? dateZhCN : dateEnUS))

const lightThemeOverrides: GlobalThemeOverrides = {
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

const darkThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#8b5cf6',
    primaryColorHover: '#a78bfa',
    primaryColorPressed: '#7c3aed',
    primaryColorSuppl: '#22d3ee',
    borderRadius: '8px',
    bodyColor: '#162235',
    baseColor: '#1d2a3f',
    cardColor: '#223049',
    modalColor: '#223049',
    popoverColor: '#223049',
    tableColor: '#223049',
    textColorBase: '#f4f7fb',
    textColor1: '#f4f7fb',
    textColor2: '#c8d2e3',
    textColor3: '#9faec4',
    borderColor: 'rgba(194, 205, 225, 0.2)',
  },
  Button: {
    color: 'rgba(37, 50, 74, 0.92)',
    colorHover: 'rgba(45, 61, 90, 0.98)',
    colorPressed: 'rgba(31, 43, 65, 0.98)',
    colorFocus: 'rgba(45, 61, 90, 0.98)',
    border: '1px solid rgba(194, 205, 225, 0.22)',
    borderHover: '1px solid rgba(167, 139, 250, 0.56)',
    borderPressed: '1px solid rgba(139, 92, 246, 0.68)',
    borderFocus: '1px solid rgba(167, 139, 250, 0.56)',
    textColor: '#c8d2e3',
    textColorHover: '#f8fafc',
    textColorPressed: '#ffffff',
    textColorFocus: '#f8fafc',
  },
  Card: {
    color: '#223049',
    borderColor: 'rgba(194, 205, 225, 0.2)',
    borderRadius: '8px',
  },
  DataTable: {
    thColor: '#283754',
    tdColor: '#223049',
    borderColor: 'rgba(194, 205, 225, 0.16)',
  },
  Input: {
    color: '#25324a',
    colorFocus: '#283754',
    textColor: '#f4f7fb',
    placeholderColor: '#9faec4',
    border: '1px solid rgba(194, 205, 225, 0.2)',
    borderHover: '1px solid rgba(167, 139, 250, 0.48)',
    borderFocus: '1px solid rgba(167, 139, 250, 0.56)',
  },
  Select: {
    peers: {
      InternalSelection: {
        color: '#25324a',
        colorActive: '#283754',
        textColor: '#f4f7fb',
        placeholderColor: '#9faec4',
        border: '1px solid rgba(194, 205, 225, 0.2)',
        borderHover: '1px solid rgba(167, 139, 250, 0.48)',
        borderActive: '1px solid rgba(167, 139, 250, 0.56)',
      },
    },
  },
  Layout: {
    color: 'transparent',
    siderColor: 'transparent',
  },
}

const themeOverrides = computed(() => (
  settings.theme === 'dark' ? darkThemeOverrides : lightThemeOverrides
))

onMounted(() => {
  settings.loadSettings()
})
</script>
