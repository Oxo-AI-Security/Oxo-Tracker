<template>
  <div class="stack">
    <ResourceTable
      eyebrow="Benchmark library"
      title="Recipes"
      :rows="store.recipes as Record<string, unknown>[]"
      :preferred-keys="['id', 'name', 'description', 'datasets', 'metrics']"
    />
    <ResourceTable
      eyebrow="Evaluation suites"
      title="Cookbooks"
      :rows="store.cookbooks as Record<string, unknown>[]"
      :preferred-keys="['id', 'name', 'description', 'recipes']"
    />
    <ResourceTable
      eyebrow="Measurement layer"
      title="Metrics"
      :rows="store.metrics"
      :preferred-keys="['id', 'name', 'description']"
    />
    <ResourceTable
      eyebrow="Prompt corpus"
      title="Datasets"
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

