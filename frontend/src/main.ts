import { createApp } from 'vue'
import {
  create,
  NAlert,
  NButton,
  NCard,
  NCheckbox,
  NConfigProvider,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NDrawer,
  NDrawerContent,
  NEmpty,
  NEllipsis,
  NForm,
  NFormItem,
  NGradientText,
  NIcon,
  NInput,
  NInputNumber,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NList,
  NListItem,
  NMessageProvider,
  NModal,
  NNotificationProvider,
  NPopconfirm,
  NPagination,
  NProgress,
  NRadioButton,
  NRadioGroup,
  NScrollbar,
  NSelect,
  NSkeleton,
  NSlider,
  NSpace,
  NSpin,
  NStatistic,
  NSwitch,
  NTag,
  NThing,
  darkTheme,
} from 'naive-ui'
import { createPinia } from 'pinia'
import App from './App.vue'
import { i18n } from './i18n'
import router from './router'
import { initializeDesktopRuntime } from './desktop/bootstrap'
import './style.css'
import './radius-system.css'

const naive = create({
  components: [
    NAlert,
    NButton,
    NCard,
    NCheckbox,
    NConfigProvider,
    NDataTable,
    NDescriptions,
    NDescriptionsItem,
    NDivider,
    NDrawer,
    NDrawerContent,
    NEmpty,
    NEllipsis,
    NForm,
    NFormItem,
    NGradientText,
    NIcon,
    NInput,
    NInputNumber,
    NLayout,
    NLayoutContent,
    NLayoutSider,
    NList,
    NListItem,
    NMessageProvider,
    NModal,
    NNotificationProvider,
    NPopconfirm,
    NPagination,
    NProgress,
    NRadioButton,
    NRadioGroup,
    NScrollbar,
    NSelect,
    NSkeleton,
    NSlider,
    NSpace,
    NSpin,
    NStatistic,
    NSwitch,
    NTag,
    NThing,
  ],
})

async function bootstrap() {
  try {
    await initializeDesktopRuntime()
    createApp(App)
      .provide('naiveTheme', darkTheme)
      .use(createPinia())
      .use(i18n)
      .use(router)
      .use(naive)
      .mount('#app')
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    const root = document.querySelector<HTMLDivElement>('#app')
    if (root) {
      root.textContent = `Oxo Tracker failed to start: ${message}`
      root.style.padding = '32px'
      root.style.fontFamily = 'system-ui, sans-serif'
      root.style.color = '#b42318'
    }
  }
}

void bootstrap()
