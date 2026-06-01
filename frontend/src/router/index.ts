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
import ConnectorList from '../views/agents/connectors/ConnectorList.vue'
import ConnectorBuilder from '../views/agents/connectors/ConnectorBuilder.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
      children: [
        { path: '', name: 'dashboard', component: DashboardView },
        { path: 'agents', name: 'agents', component: EndpointsView },
        { path: 'agents/endpoints', redirect: '/agents' },
        { path: 'agents/red-team-sessions', redirect: '/agents' },
        { path: 'agents/connectors', name: 'connectors', component: ConnectorList },
        { path: 'agents/connectors/new', name: 'connector-new', component: ConnectorBuilder },
        { path: 'agents/connectors/:id/edit', name: 'connector-edit', component: ConnectorBuilder },
        { path: 'endpoints', redirect: '/agents' },
        { path: 'payload', name: 'payload', component: PayloadView },
        { path: 'payload/cookbooks', name: 'cookbooks', component: CookbooksView },
        { path: 'payload/recipes', name: 'recipes', component: RecipesView },
        { path: 'payload/prompt-templates', name: 'prompt-templates', component: PayloadView },
        { path: 'payload/datasets', name: 'datasets', component: DatasetsView },
        { path: 'cookbooks', redirect: '/payload/cookbooks' },
        { path: 'benchmark', name: 'benchmark', component: BenchmarkView },
        { path: 'jobs/:id', name: 'job-run', component: JobRunView },
        { path: 'history', name: 'history', component: HistoryView },
        { path: 'settings', name: 'settings', component: SettingsView },
      ],
    },
  ],
})

export default router
