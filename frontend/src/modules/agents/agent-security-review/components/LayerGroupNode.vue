<template>
  <div class="agent-review-layer-group">
    <strong>{{ data.label }}</strong>
    <span>{{ data.count }} components</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ data: { label: string; count: number } }>()
</script>
