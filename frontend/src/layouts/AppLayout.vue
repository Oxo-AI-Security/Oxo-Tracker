<template>
  <n-layout has-sider class="app-shell">
    <n-layout-sider
      class="side-nav"
      :width="264"
      :collapsed-width="76"
      collapse-mode="width"
      :collapsed="collapsed"
      bordered
    >
      <n-scrollbar class="side-scrollbar" trigger="none" :x-scrollable="false">
        <div class="side-inner">
          <div class="brand">
            <div class="brand__mark">
              <n-icon size="24"><SparklesOutline /></n-icon>
            </div>
            <div v-if="!collapsed" class="brand__copy">
              <strong>Oxo Tracker</strong>
              <span>Evaluation Control</span>
            </div>
          </div>

          <n-button quaternary circle class="collapse-button" @click="collapsed = !collapsed">
            <template #icon>
              <n-icon>
                <ChevronBackOutline v-if="!collapsed" />
                <MenuOutline v-else />
              </n-icon>
            </template>
          </n-button>

          <nav class="nav-list">
            <RouterLink
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              class="nav-item"
              :class="{ 'active-route': isActiveNav(item.path) }"
            >
              <n-icon size="20"><component :is="item.icon" /></n-icon>
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </nav>

          <RouterLink
            to="/settings"
            class="settings-entry"
            :class="{ 'active-route': route.path === '/settings' }"
          >
            <n-icon size="20"><SettingsOutline /></n-icon>
            <span v-if="!collapsed">Settings</span>
          </RouterLink>
        </div>
      </n-scrollbar>
    </n-layout-sider>

    <n-layout-content class="content">
      <div class="ambient ambient-a" />
      <div class="ambient ambient-b" />
      <header class="topbar">
        <div>
          <p class="eyebrow">Secure evaluation workspace</p>
          <h1>{{ routeTitle }}</h1>
        </div>
        <n-space>
          <n-button secondary round @click="store.loadOverview">
            <template #icon>
              <n-icon><RefreshOutline /></n-icon>
            </template>
            Refresh
          </n-button>
          <n-button type="primary" round @click="router.push('/benchmark')">
            <template #icon>
              <n-icon><RocketOutline /></n-icon>
            </template>
            Run Test
          </n-button>
        </n-space>
      </header>

      <n-scrollbar class="content-scrollbar">
        <main class="page-frame">
          <n-alert v-if="store.error" type="warning" closable class="page-alert">
            {{ store.error }}
          </n-alert>
          <router-view />
        </main>
      </n-scrollbar>
    </n-layout-content>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  AnalyticsOutline,
  CubeOutline,
  FlashOutline,
  ChevronBackOutline,
  LibraryOutline,
  MenuOutline,
  RefreshOutline,
  RocketOutline,
  SparklesOutline,
  SettingsOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import { useMoonshotStore } from '../stores/moonshot'

const route = useRoute()
const router = useRouter()
const store = useMoonshotStore()
const collapsed = ref(false)

const navItems = [
  { path: '/', label: 'Dashboard', icon: AnalyticsOutline },
  { path: '/benchmark', label: 'Benchmark', icon: FlashOutline },
  { path: '/agents', label: 'Agents', icon: CubeOutline },
  { path: '/payload', label: 'Payload', icon: LibraryOutline },
  { path: '/history', label: 'History', icon: TimeOutline },
]

const routeTitle = computed(() => {
  const current = navItems.find((item) => item.path === route.path || (item.path !== '/' && route.path.startsWith(item.path)))
  if (route.path.startsWith('/jobs/')) return 'Run Details'
  if (route.path === '/payload/cookbooks') return 'Cookbooks'
  if (route.path === '/payload/recipes') return 'Recipes'
  if (route.path === '/payload/prompt-templates') return 'Prompt Templates'
  if (route.path === '/payload/datasets') return 'Datasets'
  if (route.path === '/settings') return 'Settings'
  return current?.label ?? 'Dashboard'
})

function isActiveNav(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

onMounted(() => {
  store.loadOverview()
})
</script>
