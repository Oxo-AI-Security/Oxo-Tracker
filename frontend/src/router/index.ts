import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import EndpointsView from '../views/EndpointsView.vue'
import BenchmarkView from '../views/BenchmarkView.vue'
import CookbooksView from '../views/CookbooksView.vue'
import PayloadView from '../views/PayloadView.vue'
import RecipesView from '../views/RecipesView.vue'
import DatasetsView from '../views/DatasetsView.vue'
import HistoryView from '../views/HistoryView.vue'
import JobRunView from '../views/JobRunView.vue'
import SettingsView from '../views/SettingsView.vue'
import AISettingsView from '../views/AISettingsView.vue'
import TCPForwarderView from '../views/TCPForwarderView.vue'
import ConnectorList from '../views/agents/connectors/ConnectorList.vue'
import ConnectorBuilder from '../views/agents/connectors/ConnectorBuilder.vue'
import ConnectorEndpoints from '../views/agents/connectors/ConnectorEndpoints.vue'
import AgentSecurityReviewView from '../views/agents/AgentSecurityReviewView.vue'

const dashboardBreadcrumb = [{ label: 'Dashboard', labelKey: 'route.dashboard' }]
const agentsBreadcrumb = [{ label: 'Agents', labelKey: 'route.agents', to: '/agents' }]
const connectorsBreadcrumb = [...agentsBreadcrumb, { label: 'Connectors', labelKey: 'route.connectors', to: '/agents/connectors' }]
const payloadBreadcrumb = [{ label: 'Payload', labelKey: 'route.payload', to: '/payload' }]
const benchmarkBreadcrumb = [{ label: 'Benchmark', labelKey: 'route.benchmark', to: '/benchmark' }]
const settingsBreadcrumb = [{ label: 'Settings', labelKey: 'route.settings', to: '/settings' }]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardView, meta: { breadcrumbs: dashboardBreadcrumb } },
        { path: 'agents', name: 'agents', component: EndpointsView, meta: { breadcrumbs: [{ label: 'Agents', labelKey: 'route.agents' }] } },
        { path: 'agents/endpoints', redirect: '/agents' },
        { path: 'agents/red-team-sessions', redirect: '/agents' },
        { path: 'agents/connectors', name: 'connectors', component: ConnectorList, meta: { breadcrumbs: [...agentsBreadcrumb, { label: 'Connectors', labelKey: 'route.connectors' }] } },
        { path: 'agents/connectors/new', name: 'connector-new', component: ConnectorBuilder, meta: { breadcrumbs: [...connectorsBreadcrumb, { label: 'New connector', labelKey: 'route.newConnector' }] } },
        { path: 'agents/connectors/:id/edit', name: 'connector-edit', component: ConnectorBuilder, meta: { breadcrumbs: [...connectorsBreadcrumb, { label: 'Edit connector', labelKey: 'route.editConnector' }] } },
        { path: 'agents/connectors/:id', name: 'connector-endpoints', component: ConnectorEndpoints, meta: { breadcrumbs: [...connectorsBreadcrumb, { label: 'Connector endpoints', labelKey: 'route.connectorEndpoints', param: 'id' }] } },
        { path: 'agents/security-review', name: 'agent-security-review', component: AgentSecurityReviewView, meta: { breadcrumbs: [...agentsBreadcrumb, { label: 'Security review', labelKey: 'route.securityReview' }] } },
        { path: 'endpoints', redirect: '/agents' },
        { path: 'payload', name: 'payload', component: PayloadView, meta: { breadcrumbs: [{ label: 'Payload', labelKey: 'route.payload' }] } },
        { path: 'payload/cookbooks', name: 'cookbooks', component: CookbooksView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Cookbooks', labelKey: 'route.cookbooks' }] } },
        { path: 'payload/recipes', name: 'recipes', component: RecipesView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Recipes', labelKey: 'route.recipes' }] } },
        { path: 'payload/prompt-templates', name: 'prompt-templates', component: PayloadView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Prompt templates', labelKey: 'route.promptTemplates' }] } },
        { path: 'payload/datasets', name: 'datasets', component: DatasetsView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Datasets', labelKey: 'route.datasets' }] } },
        { path: 'cookbooks', redirect: '/payload/cookbooks' },
        { path: 'benchmark', name: 'benchmark', component: BenchmarkView, meta: { breadcrumbs: [{ label: 'Benchmark', labelKey: 'route.benchmark' }] } },
        { path: 'jobs/:id', name: 'job-run', component: JobRunView, meta: { breadcrumbs: [...benchmarkBreadcrumb, { label: 'Run details', labelKey: 'route.runDetails' }] } },
        { path: 'history', name: 'history', component: HistoryView, meta: { breadcrumbs: [{ label: 'History', labelKey: 'route.history' }] } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { breadcrumbs: [{ label: 'Settings', labelKey: 'route.settings' }] } },
        { path: 'settings/ai', name: 'ai-settings', component: AISettingsView, meta: { breadcrumbs: [...settingsBreadcrumb, { label: 'AI settings', labelKey: 'route.aiSettings' }] } },
        { path: 'settings/tcp-forwarder', name: 'tcp-forwarder', component: TCPForwarderView, meta: { breadcrumbs: [...settingsBreadcrumb, { label: 'TCP port forwarder', labelKey: 'route.tcpForwarder' }] } },
      ],
    },
  ],
})

export default router
