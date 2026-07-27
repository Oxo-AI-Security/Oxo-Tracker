<template>
  <div class="settings-page-shell">
    <div class="settings-row-list">
      <RouterLink to="/settings/ai" class="settings-row-card settings-row-card--link">
        <div class="settings-row-main">
          <span class="settings-row-icon settings-row-icon--ai">
            <n-icon size="22"><SparklesOutline /></n-icon>
          </span>
          <div>
            <strong>{{ t('settings.aiTitle') }}</strong>
            <span>{{ t('settings.aiDescription') }}</span>
          </div>
        </div>
        <div class="settings-row-action">
          <span v-if="settings.ai" class="settings-active-model">
            {{ activeProviderLabel }} · {{ activeModel }}
          </span>
          <n-icon size="20"><ChevronForwardOutline /></n-icon>
        </div>
      </RouterLink>

      <RouterLink to="/settings/tcp-forwarder" class="settings-row-card settings-row-card--link">
        <div class="settings-row-main">
          <span class="settings-row-icon settings-row-icon--network">
            <n-icon size="22"><GitNetworkOutline /></n-icon>
          </span>
          <div>
            <strong>{{ t('settings.tcpTitle') }}</strong>
            <span>{{ t('settings.tcpDescription') }}</span>
          </div>
        </div>
        <div class="settings-row-action">
          <span class="settings-tool-label">{{ t('settings.generateScript') }}</span>
          <n-icon size="20"><ChevronForwardOutline /></n-icon>
        </div>
      </RouterLink>

      <article class="settings-row-card">
        <div class="settings-row-main">
          <span class="settings-row-icon">
            <n-icon size="22"><ColorPaletteOutline /></n-icon>
          </span>
          <div>
            <strong>{{ t('settings.themeTitle') }}</strong>
            <span>{{ t('settings.themeDescription') }}</span>
          </div>
        </div>
        <div class="theme-toggle settings-theme-toggle">
          <button type="button" :class="{ active: settings.theme === 'light' }" @click="settings.setTheme('light')">
            {{ t('common.light') }}
          </button>
          <button type="button" :class="{ active: settings.theme === 'dark' }" @click="settings.setTheme('dark')">
            {{ t('common.dark') }}
          </button>
        </div>
      </article>

      <article class="settings-row-card">
        <div class="settings-row-main">
          <span class="settings-row-icon settings-row-icon--language">
            <n-icon size="22"><LanguageOutline /></n-icon>
          </span>
          <div>
            <strong>{{ t('settings.languageTitle') }}</strong>
            <span>{{ t('settings.languageDescription') }}</span>
          </div>
        </div>
        <div class="theme-toggle settings-theme-toggle">
          <button type="button" :disabled="localeSaving" :class="{ active: settings.locale === 'en-US' }" @click="changeLocale('en-US')">
            {{ t('settings.english') }}
          </button>
          <button type="button" :disabled="localeSaving" :class="{ active: settings.locale === 'zh-CN' }" @click="changeLocale('zh-CN')">
            {{ t('settings.chinese') }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronForwardOutline, ColorPaletteOutline, GitNetworkOutline, LanguageOutline, SparklesOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import { useI18n } from 'vue-i18n'
import { useSettingsStore } from '../stores/settings'
import type { AppSettings } from '../types/moonshot'

const settings = useSettingsStore()
const { t } = useI18n()
const message = useMessage()
const localeSaving = ref(false)
const activeProviderLabel = computed(() => {
  const id = settings.ai?.activeProvider
  if (!id) return t('common.notConfigured')
  return settings.ai?.catalog[id]?.label || t('common.notConfigured')
})
const activeModel = computed(() => {
  const id = settings.ai?.activeProvider
  if (!id) return t('common.selectModel')
  return settings.ai?.providers[id]?.model || t('common.selectModel')
})

async function changeLocale(locale: AppSettings['locale']) {
  if (localeSaving.value || locale === settings.locale) return
  localeSaving.value = true
  try {
    await settings.setLocale(locale)
  } catch {
    message.error(t('settings.languageSaveFailed'))
  } finally {
    localeSaving.value = false
  }
}
</script>
