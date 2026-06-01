<template>
  <GlassPanel dense class="metric-card">
    <div class="metric-card__icon">
      <n-icon size="22">
        <component :is="icon" />
      </n-icon>
    </div>
    <div>
      <p class="metric-card__label">{{ label }}</p>
      <strong class="metric-card__value">{{ value }}</strong>
      <span class="metric-card__hint">{{ hint }}</span>
    </div>
  </GlassPanel>
</template>

<script setup lang="ts">
import type { Component } from 'vue'
import GlassPanel from './GlassPanel.vue'

defineProps<{
  label: string
  value: string | number
  hint: string
  icon: Component
}>()
</script>

