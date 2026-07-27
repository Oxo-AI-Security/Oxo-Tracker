import { beforeEach, describe, expect, it } from 'vitest'
import { i18n } from './index'
import enUS from '../locales/en-US'
import zhCN from '../locales/zh-CN'

function messageKeys(messages: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(messages).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return value && typeof value === 'object'
      ? messageKeys(value as Record<string, unknown>, path)
      : [path]
  })
}

describe('application locale', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'en-US'
  })

  it('uses English by default', () => {
    expect(i18n.global.locale.value).toBe('en-US')
    expect(i18n.global.t('settings.languageTitle')).toBe('Language')
  })

  it('provides Simplified Chinese messages', () => {
    i18n.global.locale.value = 'zh-CN'

    expect(i18n.global.t('settings.languageTitle')).toBe('语言')
    expect(i18n.global.t('common.runTest')).toBe('运行测试')
  })

  it('keeps both locale catalogs complete and compilable', () => {
    const englishKeys = messageKeys(enUS).sort()
    const chineseKeys = messageKeys(zhCN).sort()

    expect(chineseKeys).toEqual(englishKeys)
    for (const locale of ['en-US', 'zh-CN'] as const) {
      i18n.global.locale.value = locale
      for (const key of englishKeys) {
        expect(() => i18n.global.t(key)).not.toThrow()
      }
    }
  })
})
