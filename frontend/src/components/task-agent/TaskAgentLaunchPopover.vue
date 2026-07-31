<template>
  <NPopover
    :show="show"
    class="task-agent-popover-host"
    trigger="manual"
    placement="top-end"
    :show-arrow="false"
    :overlap="false"
    raw
    @clickoutside="closeMenu"
  >
    <template #trigger>
      <button
        class="task-agent-profile-trigger"
        type="button"
        :aria-expanded="show"
        aria-label="Attack Agent configuration"
        @click="$emit('update:show', !show)"
      >
        <span>{{ triggerModelLabel }}</span>
        <span class="task-agent-profile-intensity">{{ intensityLabel }}</span>
        <NIcon :size="16"><ChevronDownOutline /></NIcon>
      </button>
    </template>

    <section class="task-agent-codex-menu" aria-label="Attack Agent run configuration">
      <button
        type="button"
        :class="{ active: activeSubmenu === 'model' }"
        @click="toggleSubmenu('model')"
      >
        <b>{{ copy.model }}</b>
        <span>{{ triggerModelLabel }}</span>
        <NIcon :size="18"><ChevronForwardOutline /></NIcon>
      </button>
      <button
        type="button"
        :class="{ active: activeSubmenu === 'exploration' }"
        @click="toggleSubmenu('exploration')"
      >
        <b>{{ copy.exploration }}</b>
        <span>{{ intensityLabel }}</span>
        <NIcon :size="18"><ChevronForwardOutline /></NIcon>
      </button>
      <div class="task-agent-codex-divider" />
      <button class="task-agent-codex-advanced" type="button" @click="$emit('openAdvanced')">
        <b>{{ copy.advanced }}</b>
        <NIcon :size="17"><ChevronUpOutline /></NIcon>
      </button>

      <aside
        v-if="activeSubmenu === 'model'"
        class="task-agent-codex-submenu model-menu"
        :aria-label="copy.model"
      >
        <button
          v-for="option in normalizedModelOptions"
          :key="option.value"
          type="button"
          :class="{ selected: option.value === modelValue }"
          @click="selectModel(option.value)"
        >
          <span>{{ option.label }}</span>
          <NIcon v-if="option.value === modelValue" :size="20"><CheckmarkOutline /></NIcon>
        </button>
        <p v-if="normalizedModelOptions.length === 0">{{ copy.noModel }}</p>
      </aside>

      <aside
        v-if="activeSubmenu === 'exploration'"
        class="task-agent-codex-submenu"
        :aria-label="copy.exploration"
      >
        <button
          v-for="option in intensityOptions"
          :key="option.value"
          type="button"
          :class="{ selected: option.value === explorationIntensity }"
          @click="selectIntensity(option.value)"
        >
          <span>
            <b>{{ option.label }}</b>
            <small>{{ option.summary }}</small>
          </span>
          <NIcon v-if="option.value === explorationIntensity" :size="20"><CheckmarkOutline /></NIcon>
        </button>
      </aside>
    </section>
  </NPopover>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NIcon, NPopover, type SelectOption } from 'naive-ui'
import {
  CheckmarkOutline,
  ChevronDownOutline,
  ChevronForwardOutline,
  ChevronUpOutline,
} from '@vicons/ionicons5'
import type { TaskAgentExplorationIntensity } from '../../api/taskAgents'

const props = defineProps<{
  show: boolean
  locale: 'en-US' | 'zh-CN'
  modelValue: string
  modelOptions: SelectOption[]
  explorationIntensity: TaskAgentExplorationIntensity
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  'update:modelValue': [value: string]
  'update:explorationIntensity': [value: TaskAgentExplorationIntensity]
  openAdvanced: []
}>()

const activeSubmenu = ref<'model' | 'exploration' | null>(null)

watch(
  () => props.show,
  (visible) => {
    if (!visible) activeSubmenu.value = null
  },
)

const copy = computed(() =>
  props.locale === 'zh-CN'
    ? {
        model: '模型',
        exploration: '探索强度',
        advanced: '高级',
        noModel: '请先在 Settings 中配置模型',
      }
    : {
        model: 'Model',
        exploration: 'Exploration',
        advanced: 'Advanced',
        noModel: 'Configure a model in Settings first',
      },
)

const normalizedModelOptions = computed(() =>
  props.modelOptions
    .filter((option) => typeof option.value === 'string')
    .map((option) => {
      const rawLabel = String(option.label || option.value)
      return {
        label: rawLabel.includes('·')
          ? rawLabel.split('·').slice(1).join('·').trim()
          : rawLabel,
        value: String(option.value),
      }
    }),
)

const selectedModelOption = computed(() =>
  normalizedModelOptions.value.find((option) => option.value === props.modelValue),
)

const triggerModelLabel = computed(() => {
  const raw = selectedModelOption.value?.label || props.modelValue || copy.value.model
  const model = raw.includes('·') ? raw.split('·').slice(1).join('·').trim() : raw
  return model.length > 20 ? `${model.slice(0, 18)}…` : model
})

const intensityOptions = computed<
  Array<{
    label: string
    value: TaskAgentExplorationIntensity
    summary: string
  }>
>(() => {
  const zh = props.locale === 'zh-CN'
  return [
    {
      label: zh ? '轻度' : 'Light',
      value: 'light',
      summary: zh ? '最多 6 轮 · 无子 Agent' : 'Up to 6 rounds · no child agents',
    },
    {
      label: zh ? '标准' : 'Standard',
      value: 'standard',
      summary: zh ? '最多 12 轮 · 1 个子 Agent' : 'Up to 12 rounds · 1 child agent',
    },
    {
      label: zh ? '深入' : 'Deep',
      value: 'deep',
      summary: zh ? '最多 24 轮 · 2 个子 Agent' : 'Up to 24 rounds · 2 child agents',
    },
    {
      label: zh ? '极致' : 'Extreme',
      value: 'extreme',
      summary: zh ? '最多 40 轮 · 最大覆盖' : 'Up to 40 rounds · maximum coverage',
    },
  ]
})

const intensityLabel = computed(
  () =>
    intensityOptions.value.find(
      (option) => option.value === props.explorationIntensity,
    )?.label || props.explorationIntensity,
)

function toggleSubmenu(submenu: 'model' | 'exploration') {
  activeSubmenu.value = activeSubmenu.value === submenu ? null : submenu
}

function closeMenu() {
  activeSubmenu.value = null
  emit('update:show', false)
}

function selectModel(value: string) {
  emit('update:modelValue', value)
  activeSubmenu.value = null
}

function selectIntensity(value: TaskAgentExplorationIntensity) {
  emit('update:explorationIntensity', value)
  activeSubmenu.value = null
}
</script>

<style scoped>
.task-agent-profile-trigger {
  display: inline-flex;
  gap: 7px;
  align-items: center;
  justify-content: center;
  min-width: 160px;
  height: 38px;
  padding: 0 14px;
  color: #43345f;
  font-size: 13px;
  font-weight: 760;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(139, 92, 246, 0.24);
  border-radius: 999px;
  box-shadow:
    0 6px 18px rgba(88, 64, 146, 0.08),
    inset 0 1px rgba(255, 255, 255, 0.8);
  transition: background 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
}

.task-agent-profile-trigger:hover,
.task-agent-profile-trigger[aria-expanded="true"] {
  color: #6d28d9;
  background: #f7f3ff;
  border-color: rgba(124, 58, 237, 0.38);
  box-shadow:
    0 8px 22px rgba(109, 40, 217, 0.12),
    inset 0 1px rgba(255, 255, 255, 0.88);
}

.task-agent-profile-intensity {
  color: #8b78ac;
}

:global(.n-popover.task-agent-popover-host) {
  box-shadow: none !important;
}

.task-agent-codex-menu {
  position: relative;
  display: grid;
  gap: 2px;
  width: 336px;
  padding: 9px;
  color: #2f2543;
  background: #ffffff;
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 18px;
  box-shadow:
    0 22px 54px rgba(62, 42, 105, 0.2),
    0 4px 14px rgba(17, 24, 39, 0.06);
}

.task-agent-codex-menu > button {
  display: grid;
  grid-template-columns: 1fr auto 18px;
  gap: 10px;
  align-items: center;
  min-height: 42px;
  padding: 0 10px;
  color: inherit;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 11px;
}

.task-agent-codex-menu > button:hover,
.task-agent-codex-menu > button.active {
  color: #5b21b6;
  background: #f2edff;
}

.task-agent-codex-menu button:focus {
  outline: none;
}

.task-agent-codex-menu > button b {
  font-size: 14px;
  font-weight: 720;
}

.task-agent-codex-menu > button span {
  max-width: 150px;
  overflow: hidden;
  color: #8a7b9f;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-agent-codex-divider {
  height: 1px;
  margin: 4px 7px;
  background: rgba(139, 92, 246, 0.14);
}

.task-agent-codex-menu > .task-agent-codex-advanced {
  display: flex;
  gap: 6px;
  justify-content: flex-start;
  color: #756887;
}

.task-agent-codex-submenu {
  position: absolute;
  z-index: 2;
  bottom: 0;
  left: calc(100% + 8px);
  display: grid;
  gap: 2px;
  width: 316px;
  max-height: 340px;
  padding: 9px;
  overflow-y: auto;
  color: #2f2543;
  background: #ffffff;
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 18px;
  box-shadow:
    0 22px 54px rgba(62, 42, 105, 0.2),
    0 4px 14px rgba(17, 24, 39, 0.06);
  scrollbar-width: none;
}

.task-agent-codex-submenu::-webkit-scrollbar {
  display: none;
}

.task-agent-codex-submenu button {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  padding: 7px 10px;
  color: inherit;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 11px;
}

.task-agent-codex-submenu button:hover,
.task-agent-codex-submenu button.selected {
  color: #5b21b6;
  background: #f2edff;
}

.task-agent-codex-submenu button > span {
  display: grid;
  gap: 2px;
}

.task-agent-codex-submenu button b {
  font-size: 14px;
}

.task-agent-codex-submenu button small {
  color: #8a7b9f;
  font-size: 11px;
}

.task-agent-codex-submenu.model-menu button > span {
  display: block;
  overflow: hidden;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-agent-codex-submenu p {
  margin: 0;
  padding: 14px;
  color: #8a7b9f;
  font-size: 12px;
}

@media (max-width: 900px) {
  .task-agent-codex-submenu {
    right: 0;
    bottom: calc(100% + 8px);
    left: auto;
  }
}

@container (max-width: 360px) {
  .task-agent-profile-trigger {
    min-width: 118px;
    max-width: 132px;
    padding-inline: 10px;
  }

  .task-agent-profile-trigger > span:first-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .task-agent-profile-intensity {
    display: none;
  }
}
</style>
