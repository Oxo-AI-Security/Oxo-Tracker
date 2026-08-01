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
          <div
            class="brand"
            :class="{ 'brand--collapsed-action': collapsed }"
            :role="collapsed ? 'button' : undefined"
            :tabindex="collapsed ? 0 : undefined"
            :aria-label="collapsed ? 'Expand navigation' : undefined"
            :aria-expanded="collapsed ? 'false' : undefined"
            @click="expandSidebarFromBrand"
            @keydown.enter.prevent="expandSidebarFromBrand"
            @keydown.space.prevent="expandSidebarFromBrand"
          >
            <img class="brand__mark" :src="oxoLogoMark" :alt="collapsed ? 'Oxo Tracker' : 'Oxo'" />
            <div v-if="!collapsed" class="brand__copy">
              <strong>Tracker</strong>
              <span>{{ t('app.tagline') }}</span>
            </div>
          </div>

          <n-button v-if="!collapsed" quaternary circle class="collapse-button" @click="collapsed = true">
            <template #icon>
              <n-icon>
                <ChevronBackOutline />
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
            :class="{ 'active-route': route.path.startsWith('/settings') }"
          >
            <n-icon size="20"><SettingsOutline /></n-icon>
            <span v-if="!collapsed">{{ t('common.settings') }}</span>
          </RouterLink>
        </div>
      </n-scrollbar>
    </n-layout-sider>

    <n-layout-content class="content">
      <div class="ambient ambient-a" />
      <div class="ambient ambient-b" />
      <header class="topbar">
        <div
          v-if="desktopWindowControls"
          class="window-drag-strip"
          data-tauri-drag-region
          aria-hidden="true"
          @mousedown.left.prevent="startDesktopWindowDrag"
        />
        <div class="topbar-title" data-tauri-drag-region>
          <AppBreadcrumbs />
        </div>
        <div class="topbar-actions">
          <n-space align="center" class="topbar-primary-actions">
            <n-button
              secondary
              round
              :loading="refreshing"
              :disabled="refreshing"
              @click="refreshCurrentView"
            >
              <template #icon>
                <n-icon><RefreshOutline /></n-icon>
              </template>
              {{ t('common.refresh') }}
            </n-button>
            <n-button type="primary" round @click="router.push('/benchmark')">
              <template #icon>
                <n-icon><RocketOutline /></n-icon>
              </template>
              {{ t('common.runTest') }}
            </n-button>
          </n-space>
          <div
            v-if="desktopWindowControls"
            class="window-controls"
            role="group"
            :aria-label="windowControlLabels.group"
          >
            <button
              type="button"
              class="window-control"
              :title="windowControlLabels.minimize"
              :aria-label="windowControlLabels.minimize"
              @click="minimizeDesktopWindow"
            >
              <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                <path d="M3 8h10" />
              </svg>
            </button>
            <button
              type="button"
              class="window-control"
              :title="windowMaximized ? windowControlLabels.restore : windowControlLabels.maximize"
              :aria-label="windowMaximized ? windowControlLabels.restore : windowControlLabels.maximize"
              @click="toggleDesktopWindowMaximize"
            >
              <svg
                v-if="windowMaximized"
                viewBox="0 0 16 16"
                aria-hidden="true"
                focusable="false"
              >
                <rect x="5" y="3" width="8" height="8" rx="1.3" />
                <path d="M11 11v.7A1.3 1.3 0 0 1 9.7 13H4.3A1.3 1.3 0 0 1 3 11.7V6.3A1.3 1.3 0 0 1 4.3 5H5" />
              </svg>
              <svg v-else viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                <rect x="3" y="3" width="10" height="10" rx="1.5" />
              </svg>
            </button>
            <button
              type="button"
              class="window-control window-control--close"
              :title="windowControlLabels.exit"
              :aria-label="windowControlLabels.exit"
              @click="exitDialogOpen = true"
            >
              <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                <path d="m4 4 8 8M12 4l-8 8" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <n-scrollbar class="content-scrollbar">
        <main class="page-frame">
          <n-alert v-if="store.error" type="warning" closable class="page-alert">
            {{ store.error }}
          </n-alert>
          <router-view v-slot="{ Component, route: childRoute }">
            <keep-alive include="EndpointsView">
              <component
                :is="Component"
                :key="`${String(childRoute.name)}-${settings.locale}-${refreshRevision}`"
              />
            </keep-alive>
          </router-view>
        </main>
      </n-scrollbar>
    </n-layout-content>

    <ExitConfirmationModal
      v-model:show="exitDialogOpen"
      :closing="exiting"
      :locale="settings.locale"
      @cancel="exitDialogOpen = false"
      @confirm="confirmDesktopExit"
    />
  </n-layout>
</template>

<script setup lang="ts">
import type { UnlistenFn } from '@tauri-apps/api/event'
import type { Window as TauriWindow } from '@tauri-apps/api/window'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  AnalyticsOutline,
  CubeOutline,
  FlashOutline,
  ChevronBackOutline,
  LibraryOutline,
  RefreshOutline,
  RocketOutline,
  SettingsOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import { isDesktopRuntime } from '../desktop/bootstrap'
import { useMoonshotStore } from '../stores/moonshot'
import { useSettingsStore } from '../stores/settings'
import oxoLogoMark from '../assets/oxo-logo-mark.png'
import AppBreadcrumbs from '../components/AppBreadcrumbs.vue'
import ExitConfirmationModal from '../components/ExitConfirmationModal.vue'

const route = useRoute()
const router = useRouter()
const store = useMoonshotStore()
const settings = useSettingsStore()
const { t } = useI18n()
const collapsed = ref(false)
const refreshing = ref(false)
const refreshRevision = ref(0)
const desktopWindowControls = isDesktopRuntime()
const windowMaximized = ref(false)
const exitDialogOpen = ref(false)
const exiting = ref(false)
let desktopWindow: TauriWindow | null = null
let removeWindowResizeListener: UnlistenFn | undefined

const windowControlLabels = computed(() => (
  settings.locale === 'zh-CN'
    ? {
        group: '窗口控制',
        minimize: '最小化',
        maximize: '最大化',
        restore: '还原窗口',
        exit: '退出应用',
      }
    : {
        group: 'Window controls',
        minimize: 'Minimize',
        maximize: 'Maximize',
        restore: 'Restore window',
        exit: 'Exit Oxo Tracker',
      }
))

async function resolveDesktopWindow() {
  if (!desktopWindowControls) return null
  if (!desktopWindow) {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    desktopWindow = getCurrentWindow()
  }
  return desktopWindow
}

async function syncWindowMaximizedState() {
  const appWindow = await resolveDesktopWindow()
  if (!appWindow) return
  windowMaximized.value = await appWindow.isMaximized()
  document.documentElement.dataset.windowMaximized = String(windowMaximized.value)
}

async function minimizeDesktopWindow() {
  try {
    await (await resolveDesktopWindow())?.minimize()
  } catch (error) {
    console.error('Failed to minimize the desktop window', error)
  }
}

async function confirmDesktopExit() {
  if (exiting.value) return
  exiting.value = true
  try {
    const appWindow = await resolveDesktopWindow()
    if (!appWindow) {
      window.close()
      return
    }
    await appWindow.close()
  } catch (error) {
    exiting.value = false
    console.error('Failed to close the desktop window', error)
  }
}

async function toggleDesktopWindowMaximize() {
  try {
    const appWindow = await resolveDesktopWindow()
    if (!appWindow) return
    if (await appWindow.isMaximized()) {
      await appWindow.unmaximize()
    } else {
      await appWindow.maximize()
    }
    await syncWindowMaximizedState()
  } catch (error) {
    console.error('Failed to resize the desktop window', error)
  }
}

function startDesktopWindowDrag() {
  const appWindow = desktopWindow
  if (!appWindow) return
  void appWindow.startDragging().catch((error) => {
    console.error('Failed to start dragging the desktop window', error)
  })
}

async function refreshCurrentView() {
  if (refreshing.value) return
  refreshing.value = true
  try {
    await Promise.allSettled([
      store.loadOverview(),
      settings.loadSettings(),
    ])
    refreshRevision.value += 1
    await nextTick()
  } finally {
    refreshing.value = false
  }
}

function expandSidebarFromBrand() {
  if (collapsed.value) {
    collapsed.value = false
  }
}

const navItems = computed(() => [
  { path: '/', label: t('nav.dashboard'), icon: AnalyticsOutline },
  { path: '/benchmark', label: t('nav.benchmark'), icon: FlashOutline },
  { path: '/agents', label: t('nav.agents'), icon: CubeOutline },
  { path: '/payload', label: t('nav.payload'), icon: LibraryOutline },
  { path: '/history', label: t('nav.history'), icon: TimeOutline },
])

function isActiveNav(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

onMounted(async () => {
  store.loadOverview()
  if (!desktopWindowControls) return
  try {
    const appWindow = await resolveDesktopWindow()
    if (!appWindow) return
    await syncWindowMaximizedState()
    removeWindowResizeListener = await appWindow.onResized(() => {
      void syncWindowMaximizedState()
    })
  } catch (error) {
    console.error('Failed to initialize desktop window controls', error)
  }
})

onBeforeUnmount(() => {
  removeWindowResizeListener?.()
})
</script>
