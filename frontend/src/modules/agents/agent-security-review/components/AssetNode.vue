<template>
  <div
    class="agent-review-asset-node"
    :class="[data.palette?.className, `status-${data.status}`, `risk-${data.risk_hint || 'unknown'}`, `role-${data.workflowRole || 'trigger'}`, { approval: data.requires_approval }]"
  >
    <Handle v-if="data.workflowRole === 'dependency'" id="top" type="target" :position="Position.Top" />
    <div class="agent-review-asset-node-top">
      <span>{{ data.palette?.icon || 'A' }}</span>
      <div>
        <strong>{{ data.name || data.label }}</strong>
        <small>{{ data.subtitle || data.palette?.label || data.asset_type }}</small>
      </div>
      <em v-if="data.workflowRole !== 'dependency'">{{ statusLabel }}</em>
    </div>
    <p v-if="data.workflowRole !== 'dependency'">{{ shortDescription }}</p>
    <div v-if="data.workflowRole === 'dependency'" class="agent-review-asset-node-caption">
      <strong>{{ data.name || data.label }}</strong>
      <small>{{ data.subtitle || data.palette?.label || data.asset_type }}</small>
    </div>
    <div v-else class="agent-review-asset-node-tags">
      <i v-if="data.portLabel">{{ data.portLabel }}</i>
      <i v-if="data.access_mode && data.access_mode !== 'unknown'">{{ data.access_mode }}</i>
      <i v-if="data.requires_approval">approval</i>
      <i v-if="data.risk_hint && data.risk_hint !== 'unknown'">{{ data.risk_hint }}</i>
    </div>
    <Handle v-if="data.workflowRole !== 'dependency'" id="left" type="target" :position="Position.Left" />
    <Handle v-if="data.workflowRole !== 'dependency'" id="right" type="source" :position="Position.Right" />
    <Handle v-if="data.workflowRole !== 'dependency'" id="bottom" type="source" :position="Position.Bottom" />
  </div>
</template>

<script setup lang="ts">
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'

const props = defineProps<{ data: Record<string, any> }>()

const shortDescription = computed(() => {
  const value = String(props.data.description || '')
  return value.length > 96 ? `${value.slice(0, 93)}...` : value
})

const statusLabel = computed(() => {
  const value = String(props.data.status || '')
  return value === 'present' ? '' : value
})
</script>
