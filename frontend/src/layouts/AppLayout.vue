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

          <div class="side-footer-actions">
            <RouterLink
              to="/settings"
              class="settings-entry"
              :class="{ 'active-route': route.path.startsWith('/settings') }"
            >
              <n-icon size="20"><SettingsOutline /></n-icon>
              <span v-if="!collapsed">{{ t('common.settings') }}</span>
            </RouterLink>
            <button
              type="button"
              class="settings-entry product-details-entry"
              :aria-label="collapsed ? t('productInfo.label') : undefined"
              @click="openProductDetails"
            >
              <n-icon size="20"><InformationCircleOutline /></n-icon>
              <span v-if="!collapsed">{{ t('productInfo.label') }}</span>
              <span
                v-if="!collapsed"
                class="product-details-entry__badge"
                :class="{ 'product-details-entry__badge--update': cachedUpdatePending }"
              >
                {{ cachedUpdatePending ? t('productInfo.updateBadge') : t('productInfo.preview') }}
              </span>
            </button>
          </div>
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

    <n-modal v-model:show="productDetailsOpen" class="product-details-modal" :bordered="false">
      <section class="product-details-card" role="dialog" aria-modal="true" aria-labelledby="product-details-title">
        <button class="product-details-close" type="button" :aria-label="t('productInfo.close')" @click="productDetailsOpen = false">
          <n-icon><CloseOutline /></n-icon>
        </button>

        <header class="product-details-hero">
          <div class="product-details-brand-mark">
            <img :src="oxoLogoMark" alt="Oxo Tracker" />
          </div>
          <div class="product-details-heading">
            <span class="product-details-preview-badge"><i /> {{ t('productInfo.previewRelease') }}</span>
            <h2 id="product-details-title">Oxo Tracker</h2>
            <p>{{ t('productInfo.subtitle') }}</p>
          </div>
          <div class="product-details-version">
            <small>{{ t('productInfo.currentVersion') }}</small>
            <strong>v{{ productVersion }}</strong>
          </div>
        </header>

        <div class="product-details-intro">
          <span><n-icon><SparklesOutline /></n-icon></span>
          <div>
            <strong>{{ t('productInfo.introTitle') }}</strong>
            <p>{{ t('productInfo.introDescription') }}</p>
          </div>
        </div>

        <section class="product-update-panel" :class="`product-update-panel--${updateStatus}`">
          <div class="product-update-panel__summary">
            <span class="product-update-panel__indicator" aria-hidden="true" />
            <div>
              <small>{{ t('productInfo.softwareUpdate') }}</small>
              <strong>{{ updateHeadline }}</strong>
              <p>{{ updateDescription }}</p>
            </div>
          </div>

          <dl v-if="latestVersion || updateCheckedAt" class="product-update-panel__meta">
            <div v-if="latestVersion">
              <dt>{{ t('productInfo.latestVersion') }}</dt>
              <dd>v{{ latestVersion }}</dd>
            </div>
            <div v-if="updateCheckedAt">
              <dt>{{ t('productInfo.lastChecked') }}</dt>
              <dd>{{ formattedUpdateCheckedAt }}</dd>
            </div>
          </dl>

          <div v-if="updateNotes && cachedUpdatePending" class="product-update-panel__notes">
            <strong>{{ t('productInfo.updateNotes') }}</strong>
            <p>{{ updateNotes }}</p>
          </div>

          <div v-if="updateStatus === 'downloading' || updateStatus === 'installing'" class="product-update-progress">
            <div>
              <span>{{ updateStatus === 'installing' ? t('productInfo.installing') : t('productInfo.downloading') }}</span>
              <strong v-if="updateProgress !== null">{{ updateProgress }}%</strong>
            </div>
            <div class="product-update-progress__track">
              <i :class="{ indeterminate: updateProgress === null }" :style="updateProgress === null ? undefined : { width: `${updateProgress}%` }" />
            </div>
          </div>

          <div class="product-update-panel__actions">
            <span v-if="hasActiveJobs && cachedUpdatePending">{{ t('productInfo.runningJobsBlocked') }}</span>
            <button
              v-if="updateStatus === 'available'"
              type="button"
              class="product-update-action product-update-action--primary"
              :disabled="!pendingUpdate || hasActiveJobs"
              @click="installAvailableUpdate"
            >
              {{ t('productInfo.downloadAndInstall') }}
            </button>
            <button
              v-if="updateStatus === 'error' || updateStatus === 'current'"
              type="button"
              class="product-update-action product-update-action--secondary"
              @click="checkProductUpdate"
            >
              {{ t('productInfo.checkAgain') }}
            </button>
          </div>
        </section>

        <div class="product-details-grid">
          <article>
            <span><n-icon><LayersOutline /></n-icon></span>
            <small>{{ t('productInfo.releaseChannel') }}</small>
            <strong>{{ t('productInfo.preview') }}</strong>
            <p>{{ t('productInfo.previewDescription') }}</p>
          </article>
          <article>
            <span><n-icon><DesktopOutline /></n-icon></span>
            <small>{{ t('productInfo.application') }}</small>
            <strong>{{ desktopWindowControls ? t('productInfo.desktopClient') : t('productInfo.developmentClient') }}</strong>
            <p>{{ t('productInfo.applicationDescription') }}</p>
          </article>
          <article>
            <span><n-icon><ShieldCheckmarkOutline /></n-icon></span>
            <small>{{ t('productInfo.securityFocus') }}</small>
            <strong>{{ t('productInfo.aiAssurance') }}</strong>
            <p>{{ t('productInfo.securityDescription') }}</p>
          </article>
        </div>

        <footer class="product-details-footer">
          <p><strong>{{ t('productInfo.previewNotice') }}</strong> {{ t('productInfo.previewNoticeText') }}</p>
          <button type="button" @click="productDetailsOpen = false">{{ t('productInfo.gotIt') }}</button>
        </footer>
      </section>
    </n-modal>
  </n-layout>
</template>

<script setup lang="ts">
import type { UnlistenFn } from '@tauri-apps/api/event'
import type { Window as TauriWindow } from '@tauri-apps/api/window'
import type { Update } from '@tauri-apps/plugin-updater'
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import {
  AnalyticsOutline,
  CubeOutline,
  CloseOutline,
  DesktopOutline,
  FlashOutline,
  ChevronBackOutline,
  InformationCircleOutline,
  LayersOutline,
  LibraryOutline,
  RefreshOutline,
  RocketOutline,
  SettingsOutline,
  ShieldCheckmarkOutline,
  SparklesOutline,
  TimeOutline,
} from '@vicons/ionicons5'
import { isDesktopRuntime } from '../desktop/bootstrap'
import {
  checkForDesktopUpdate,
  downloadInstallAndRelaunch,
  hasPendingCachedUpdate,
  loadCachedUpdateState,
  saveCachedUpdateState,
  shouldCheckForUpdateOnStartup,
  type CachedUpdateState,
} from '../desktop/updater'
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
const desktopUpdaterAvailable = desktopWindowControls && !import.meta.env.DEV
const windowMaximized = ref(false)
const exitDialogOpen = ref(false)
const productDetailsOpen = ref(false)
const productVersion = ref('0.1.0')
const updateStatus = ref<'idle' | 'checking' | 'available' | 'current' | 'error' | 'downloading' | 'installing' | 'unavailable'>('idle')
const latestVersion = ref('')
const updateNotes = ref('')
const updateCheckedAt = ref('')
const updateError = ref('')
const updateProgress = ref<number | null>(null)
const exiting = ref(false)
let desktopWindow: TauriWindow | null = null
let removeWindowResizeListener: UnlistenFn | undefined
let pendingUpdate: Update | null = null
let updateCheckPromise: Promise<void> | null = null

const cachedUpdatePending = computed(() => (
  latestVersion.value ? hasPendingCachedUpdate({
    checkedAt: updateCheckedAt.value,
    latestVersion: latestVersion.value,
    notes: updateNotes.value,
    pubDate: null,
  }, productVersion.value) : false
))
const hasActiveJobs = computed(() => store.jobs.some((job) => (
  ['queued', 'running', 'running_with_errors', 'paused'].includes(job.status)
)))
const formattedUpdateCheckedAt = computed(() => {
  if (!updateCheckedAt.value) return ''
  const parsed = new Date(updateCheckedAt.value)
  if (Number.isNaN(parsed.getTime())) return updateCheckedAt.value
  return new Intl.DateTimeFormat(settings.locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed)
})
const updateHeadline = computed(() => ({
  idle: t('productInfo.updateIdle'),
  checking: t('productInfo.checkingUpdate'),
  available: t('productInfo.updateAvailable'),
  current: t('productInfo.upToDate'),
  error: t('productInfo.checkFailed'),
  downloading: t('productInfo.downloadingUpdate'),
  installing: t('productInfo.installingUpdate'),
  unavailable: t('productInfo.updateUnavailable'),
}[updateStatus.value]))
const updateDescription = computed(() => {
  if (updateStatus.value === 'error' && updateError.value) return updateError.value
  if (updateStatus.value === 'available') {
    if (updateError.value) return updateError.value
    return hasActiveJobs.value ? t('productInfo.runningJobsBlocked') : t('productInfo.updateWillRestart')
  }
  return ({
    idle: t('productInfo.updateIdleDescription'),
    checking: t('productInfo.checkingDescription'),
    current: t('productInfo.upToDateDescription'),
    downloading: t('productInfo.downloadingDescription'),
    installing: t('productInfo.installingDescription'),
    unavailable: t('productInfo.developmentUnavailable'),
  } as Record<string, string>)[updateStatus.value] || ''
})

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

function applyCachedUpdateState(cache: CachedUpdateState | null) {
  if (!cache) return
  latestVersion.value = cache.latestVersion
  updateNotes.value = cache.notes
  updateCheckedAt.value = cache.checkedAt
  updateStatus.value = hasPendingCachedUpdate(cache, productVersion.value) ? 'available' : 'current'
}

async function checkProductUpdate() {
  if (!desktopUpdaterAvailable) {
    updateStatus.value = 'unavailable'
    return
  }
  if (updateCheckPromise) return updateCheckPromise

  updateCheckPromise = (async () => {
    updateStatus.value = 'checking'
    updateError.value = ''
    try {
      const update = await checkForDesktopUpdate()
      const previousUpdate = pendingUpdate
      pendingUpdate = update
      if (previousUpdate && previousUpdate !== update) await previousUpdate.close()

      const cache: CachedUpdateState = {
        checkedAt: new Date().toISOString(),
        latestVersion: update?.version || productVersion.value,
        notes: update?.body || '',
        pubDate: update?.date || null,
      }
      saveCachedUpdateState(cache)
      applyCachedUpdateState(cache)
      updateStatus.value = update ? 'available' : 'current'
    } catch (error) {
      updateStatus.value = 'error'
      updateError.value = error instanceof Error ? error.message : String(error)
      console.warn('Unable to check for an Oxo Tracker update', error)
    } finally {
      updateCheckPromise = null
    }
  })()
  return updateCheckPromise
}

function openProductDetails() {
  productDetailsOpen.value = true
  void checkProductUpdate()
}

async function installAvailableUpdate() {
  if (!pendingUpdate || updateStatus.value !== 'available') return
  await store.loadOverview()
  if (hasActiveJobs.value) return

  updateStatus.value = 'downloading'
  updateProgress.value = null
  updateError.value = ''
  try {
    await downloadInstallAndRelaunch(pendingUpdate, (progress) => {
      updateProgress.value = progress.percent
      if (progress.finished) updateStatus.value = 'installing'
    })
  } catch (error) {
    updateStatus.value = 'available'
    updateError.value = error instanceof Error ? error.message : String(error)
    console.error('Unable to install the Oxo Tracker update', error)
  }
}

onMounted(async () => {
  store.loadOverview()
  if (!desktopWindowControls) return
  try {
    const { getVersion } = await import('@tauri-apps/api/app')
    productVersion.value = await getVersion()
  } catch (error) {
    console.warn('Unable to read the desktop application version', error)
  }
  const cachedUpdate = loadCachedUpdateState()
  applyCachedUpdateState(cachedUpdate)
  if (shouldCheckForUpdateOnStartup(cachedUpdate, productVersion.value)) {
    void checkProductUpdate()
  }
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
  if (pendingUpdate) void pendingUpdate.close()
  pendingUpdate = null
})
</script>
