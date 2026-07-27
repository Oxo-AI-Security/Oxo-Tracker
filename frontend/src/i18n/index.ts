import { createI18n } from 'vue-i18n'
import enUS from '../locales/en-US'
import zhCN from '../locales/zh-CN'
import type { AppSettings } from '../types/moonshot'

export const i18n = createI18n({
  legacy: false,
  locale: 'en-US',
  fallbackLocale: 'en-US',
  messages: {
    'en-US': enUS,
    'zh-CN': zhCN,
  },
})

export function setI18nLocale(locale: AppSettings['locale']) {
  i18n.global.locale.value = locale
  document.documentElement.lang = locale
}

export function translateSource(key: string, named?: Record<string, string | number>) {
  return named ? i18n.global.t(key, named) : i18n.global.t(key)
}
