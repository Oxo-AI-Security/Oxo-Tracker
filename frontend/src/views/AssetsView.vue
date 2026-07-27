<template>
  <div class="stack">
    <ResourceTable
      eyebrow="Benchmark library"
      :title="$t('auto.9fb1092f32d4')"
      :rows="store.recipes as Record<string, unknown>[]"
      :preferred-keys="['id', 'name', 'description', 'datasets', 'metrics']"
    />
    <ResourceTable
      eyebrow="Evaluation suites"
      :title="$t('auto.3a27713963ce')"
      :rows="store.cookbooks as Record<string, unknown>[]"
      :preferred-keys="['id', 'name', 'description', 'recipes']"
    />
    <ResourceTable
      eyebrow="Measurement layer"
      :title="$t('auto.ddf6a1f0ce8c')"
      :rows="store.metrics"
      :preferred-keys="['id', 'name', 'description']"
    />
    <ResourceTable
      eyebrow="Prompt corpus"
      :title="$t('auto.93a7f22476e9')"
      :rows="store.datasets"
      :preferred-keys="['id', 'name', 'description', 'num_of_dataset_prompts']"
    />
  </div>
</template>

<script setup lang="ts">
import ResourceTable from '../components/ResourceTable.vue'
import { useMoonshotStore } from '../stores/moonshot'

const store = useMoonshotStore()
</script>

