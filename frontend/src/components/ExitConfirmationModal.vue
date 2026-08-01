<template>
  <n-modal
    :show="show"
    :mask-closable="!closing"
    :close-on-esc="!closing"
    :auto-focus="true"
    :trap-focus="true"
    transform-origin="center"
    @update:show="updateShow"
  >
    <section
      class="exit-confirmation"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      :aria-describedby="descriptionId"
    >
      <span class="exit-confirmation__glow" aria-hidden="true" />

      <div class="exit-confirmation__icon" aria-hidden="true">
        <n-icon><PowerOutline /></n-icon>
      </div>

      <div class="exit-confirmation__copy">
        <span class="exit-confirmation__eyebrow">{{ copy.eyebrow }}</span>
        <h2 :id="titleId">{{ copy.title }}</h2>
        <p :id="descriptionId">{{ copy.description }}</p>
      </div>

      <div class="exit-confirmation__notice">
        <span class="exit-confirmation__notice-icon" aria-hidden="true">
          <n-icon><ShieldCheckmarkOutline /></n-icon>
        </span>
        <span>
          <strong>{{ copy.noticeTitle }}</strong>
          <small>{{ copy.noticeDescription }}</small>
        </span>
      </div>

      <footer class="exit-confirmation__actions">
        <n-button size="large" secondary round :disabled="closing" @click="$emit('cancel')">
          {{ copy.cancel }}
        </n-button>
        <n-button size="large" type="error" round :loading="closing" @click="$emit('confirm')">
          <template #icon><n-icon><LogOutOutline /></n-icon></template>
          {{ copy.confirm }}
        </n-button>
      </footer>
    </section>
  </n-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { LogOutOutline, PowerOutline, ShieldCheckmarkOutline } from '@vicons/ionicons5'

const props = defineProps<{
  show: boolean
  closing: boolean
  locale: 'zh-CN' | 'en-US'
}>()

const emit = defineEmits<{
  cancel: []
  confirm: []
  'update:show': [value: boolean]
}>()

const titleId = 'oxo-exit-confirmation-title'
const descriptionId = 'oxo-exit-confirmation-description'

const copy = computed(() => (
  props.locale === 'zh-CN'
    ? {
        eyebrow: '退出 Oxo Tracker',
        title: '要结束本次使用吗？',
        description: '确认后将关闭桌面窗口，并停止随应用运行的本地服务。',
        noticeTitle: '不会删除任何数据',
        noticeDescription: '数据集、测试记录和应用设置都会保留。',
        cancel: '继续使用',
        confirm: '确认退出',
      }
    : {
        eyebrow: 'Exit Oxo Tracker',
        title: 'Finish this session?',
        description: 'The desktop window and its local application service will be closed.',
        noticeTitle: 'Your data stays safe',
        noticeDescription: 'Datasets, test history, and application settings are preserved.',
        cancel: 'Keep working',
        confirm: 'Exit application',
      }
))

function updateShow(value: boolean) {
  if (!props.closing) emit('update:show', value)
}
</script>

<style scoped>
.exit-confirmation {
  position: relative;
  width: min(470px, calc(100vw - 32px));
  padding: 30px;
  overflow: hidden;
  color: #172033;
  background:
    radial-gradient(circle at 92% 2%, rgba(139, 92, 246, 0.16), transparent 34%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.99), rgba(249, 247, 255, 0.98));
  border: 1px solid rgba(124, 58, 237, 0.16);
  border-radius: 26px;
  box-shadow:
    0 32px 90px rgba(30, 41, 59, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.94);
}

.exit-confirmation__glow {
  position: absolute;
  top: -74px;
  right: -58px;
  width: 190px;
  height: 190px;
  pointer-events: none;
  background: rgba(139, 92, 246, 0.12);
  border-radius: 999px;
  filter: blur(12px);
}

.exit-confirmation__icon {
  position: relative;
  display: grid;
  width: 58px;
  height: 58px;
  margin-bottom: 22px;
  place-items: center;
  color: #dc2626;
  background: linear-gradient(145deg, #fff7f7, #feecec);
  border: 1px solid rgba(239, 68, 68, 0.18);
  border-radius: 18px;
  box-shadow: 0 14px 30px rgba(220, 38, 38, 0.12);
}

.exit-confirmation__icon .n-icon {
  font-size: 27px;
}

.exit-confirmation__copy {
  position: relative;
}

.exit-confirmation__eyebrow {
  color: #7c3aed;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.exit-confirmation h2 {
  margin: 7px 0 0;
  color: #111827;
  font-size: 27px;
  font-weight: 850;
  line-height: 1.2;
  letter-spacing: -0.025em;
}

.exit-confirmation__copy p {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.7;
}

.exit-confirmation__notice {
  position: relative;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  margin-top: 22px;
  padding: 14px 16px;
  background: rgba(245, 243, 255, 0.76);
  border: 1px solid rgba(139, 92, 246, 0.13);
  border-radius: 16px;
}

.exit-confirmation__notice-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  color: #6d28d9;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 7px 18px rgba(76, 29, 149, 0.09);
}

.exit-confirmation__notice-icon .n-icon {
  font-size: 20px;
}

.exit-confirmation__notice > span:last-child {
  display: grid;
  gap: 3px;
}

.exit-confirmation__notice strong {
  color: #3b276a;
  font-size: 13px;
}

.exit-confirmation__notice small {
  color: #766b8e;
  font-size: 12px;
  line-height: 1.5;
}

.exit-confirmation__actions {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.exit-confirmation__actions .n-button {
  width: 100%;
  min-height: 44px;
  font-weight: 800;
}

:global(:root[data-theme="dark"]) .exit-confirmation {
  color: #eef2ff;
  background:
    radial-gradient(circle at 92% 2%, rgba(139, 92, 246, 0.2), transparent 34%),
    linear-gradient(145deg, rgba(28, 39, 59, 0.99), rgba(24, 32, 49, 0.99));
  border-color: rgba(167, 139, 250, 0.22);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.48);
}

:global(:root[data-theme="dark"]) .exit-confirmation h2 {
  color: #f8fafc;
}

:global(:root[data-theme="dark"]) .exit-confirmation__copy p {
  color: #aebbd0;
}

:global(:root[data-theme="dark"]) .exit-confirmation__notice {
  background: rgba(72, 51, 122, 0.26);
  border-color: rgba(167, 139, 250, 0.18);
}

:global(:root[data-theme="dark"]) .exit-confirmation__notice-icon {
  color: #c4b5fd;
  background: rgba(15, 23, 42, 0.76);
}

:global(:root[data-theme="dark"]) .exit-confirmation__notice strong {
  color: #ede9fe;
}

:global(:root[data-theme="dark"]) .exit-confirmation__notice small {
  color: #b9add3;
}

@media (max-width: 520px) {
  .exit-confirmation {
    padding: 24px;
    border-radius: 22px;
  }

  .exit-confirmation__actions {
    grid-template-columns: 1fr;
  }
}
</style>
