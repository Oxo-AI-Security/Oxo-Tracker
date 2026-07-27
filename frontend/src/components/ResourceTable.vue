<template>
  <GlassPanel>
    <div class="section-heading">
      <div>
        <p class="eyebrow">{{ eyebrow }}</p>
        <h2>{{ title }}</h2>
      </div>
      <n-tag round :bordered="false" type="info">{{ rows.length }} {{ $t('auto.86761b63a7bd') }}</n-tag>
    </div>

    <n-data-table
      v-if="rows.length"
      :columns="columns"
      :data="rows"
      :pagination="{ pageSize: 8 }"
      :bordered="false"
      size="small"
    />
    <n-empty v-else :description="$t('auto.5c52a29e440a')" />
  </GlassPanel>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import type { DataTableColumns } from 'naive-ui'
import GlassPanel from './GlassPanel.vue'

const props = defineProps<{
  eyebrow: string
  title: string
  rows: Record<string, unknown>[]
  preferredKeys?: string[]
}>()

const columns = computed<DataTableColumns<Record<string, unknown>>>(() => {
  const keys = props.preferredKeys?.length
    ? props.preferredKeys
    : Object.keys(props.rows[0] ?? {}).slice(0, 5)

  return keys.map((key) => ({
    title: key,
    key,
    ellipsis: { tooltip: true },
    render(row) {
      const value = row[key]
      if (Array.isArray(value)) return value.join(', ')
      if (value && typeof value === 'object') return h('span', JSON.stringify(value))
      return String(value ?? '')
    },
  }))
})
</script>

