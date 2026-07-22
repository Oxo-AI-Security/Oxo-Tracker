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
import ConnectorList from '../views/agents/connectors/ConnectorList.vue'
import ConnectorBuilder from '../views/agents/connectors/ConnectorBuilder.vue'
import ConnectorEndpoints from '../views/agents/connectors/ConnectorEndpoints.vue'
import AgentSecurityReviewView from '../views/agents/AgentSecurityReviewView.vue'

const dashboardBreadcrumb = [{ label: 'Dashboard' }]
const agentsBreadcrumb = [{ label: 'Agents', to: '/agents' }]
const connectorsBreadcrumb = [...agentsBreadcrumb, { label: 'Connectors', to: '/agents/connectors' }]
const payloadBreadcrumb = [{ label: 'Payload', to: '/payload' }]
const benchmarkBreadcrumb = [{ label: 'Benchmark', to: '/benchmark' }]
const settingsBreadcrumb = [{ label: 'Settings', to: '/settings' }]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardView, meta: { breadcrumbs: dashboardBreadcrumb } },
        { path: 'agents', name: 'agents', component: EndpointsView, meta: { breadcrumbs: [{ label: 'Agents' }] } },
        { path: 'agents/endpoints', redirect: '/agents' },
        { path: 'agents/red-team-sessions', redirect: '/agents' },
        { path: 'agents/connectors', name: 'connectors', component: ConnectorList, meta: { breadcrumbs: [...agentsBreadcrumb, { label: 'Connectors' }] } },
        { path: 'agents/connectors/new', name: 'connector-new', component: ConnectorBuilder, meta: { breadcrumbs: [...connectorsBreadcrumb, { label: 'New connector' }] } },
        { path: 'agents/connectors/:id/edit', name: 'connector-edit', component: ConnectorBuilder, meta: { breadcrumbs: [...connectorsBreadcrumb, { label: 'Edit connector' }] } },
        { path: 'agents/connectors/:id', name: 'connector-endpoints', component: ConnectorEndpoints, meta: { breadcrumbs: [...connectorsBreadcrumb, { label: 'Connector endpoints', param: 'id' }] } },
        { path: 'agents/security-review', name: 'agent-security-review', component: AgentSecurityReviewView, meta: { breadcrumbs: [...agentsBreadcrumb, { label: 'Security review' }] } },
        { path: 'endpoints', redirect: '/agents' },
        { path: 'payload', name: 'payload', component: PayloadView, meta: { breadcrumbs: [{ label: 'Payload' }] } },
        { path: 'payload/cookbooks', name: 'cookbooks', component: CookbooksView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Cookbooks' }] } },
        { path: 'payload/recipes', name: 'recipes', component: RecipesView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Recipes' }] } },
        { path: 'payload/prompt-templates', name: 'prompt-templates', component: PayloadView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Prompt templates' }] } },
        { path: 'payload/datasets', name: 'datasets', component: DatasetsView, meta: { breadcrumbs: [...payloadBreadcrumb, { label: 'Datasets' }] } },
        { path: 'cookbooks', redirect: '/payload/cookbooks' },
        { path: 'benchmark', name: 'benchmark', component: BenchmarkView, meta: { breadcrumbs: [{ label: 'Benchmark' }] } },
        { path: 'jobs/:id', name: 'job-run', component: JobRunView, meta: { breadcrumbs: [...benchmarkBreadcrumb, { label: 'Run details' }] } },
        { path: 'history', name: 'history', component: HistoryView, meta: { breadcrumbs: [{ label: 'History' }] } },
        { path: 'settings', name: 'settings', component: SettingsView, meta: { breadcrumbs: [{ label: 'Settings' }] } },
        { path: 'settings/ai', name: 'ai-settings', component: AISettingsView, meta: { breadcrumbs: [...settingsBreadcrumb, { label: 'AI settings' }] } },
      ],
    },
  ],
})

export default router
