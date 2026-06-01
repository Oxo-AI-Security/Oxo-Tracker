<template>
  <section class="glass-panel" :class="{ dense }">
    <slot />
  </section>
</template>

<script setup lang="ts">
defineProps<{ dense?: boolean }>()
</script>

