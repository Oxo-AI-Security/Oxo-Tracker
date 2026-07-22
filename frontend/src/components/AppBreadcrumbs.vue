<template>
  <nav class="app-breadcrumbs" :class="{ 'app-breadcrumbs--nested': breadcrumbs.length > 1 }" aria-label="Breadcrumb">
    <ol>
      <li v-for="(crumb, index) in breadcrumbs" :key="`${crumb.label}-${index}`">
        <n-icon v-if="index > 0" class="app-breadcrumbs__separator" aria-hidden="true">
          <ChevronForwardOutline />
        </n-icon>
        <RouterLink v-if="crumb.to && index < breadcrumbs.length - 1" :to="crumb.to">
          <span>{{ crumb.label }}</span>
        </RouterLink>
        <span v-else class="app-breadcrumbs__current" :aria-current="index === breadcrumbs.length - 1 ? 'page' : undefined">
          <span>{{ crumb.label }}</span>
        </span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { ChevronForwardOutline } from '@vicons/ionicons5'

interface BreadcrumbDefinition {
  label: string
  to?: string
  param?: string
  prefix?: string
}

interface BreadcrumbItem {
  label: string
  to?: string
}

const route = useRoute()

function humanize(value: string) {
  return decodeURIComponent(value)
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

const breadcrumbs = computed<BreadcrumbItem[]>(() => {
  const definitions = (route.meta.breadcrumbs || []) as BreadcrumbDefinition[]
  const items = definitions.map((definition) => {
    const parameter = definition.param ? route.params[definition.param] : undefined
    const rawParameter = Array.isArray(parameter) ? parameter[0] : parameter
    const parameterLabel = rawParameter ? humanize(String(rawParameter)) : ''
    return {
      label: parameterLabel ? `${definition.prefix || ''}${parameterLabel}` : definition.label,
      to: definition.to,
    }
  })

  return items.length ? items : [{ label: 'Dashboard' }]
})
</script>
