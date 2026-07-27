<template>
  <div class="workflow-shell">
    <header class="workflow-heading">
      <div>
        <strong>{{ $t('auto.6e85c1f0d4fa') }}</strong>
        <small>{{ $t('auto.5dc96f624ea5') }}</small>
      </div>
      <span v-if="currentNode" class="workflow-live"><i></i>{{ $t('auto.a3856d306f72') }} {{ activeLabel }}</span>
    </header>

    <div v-if="definition" class="workflow-board">
      <section class="workflow-agent-row">
        <button
          v-for="agent in agentCards"
          :key="agent.id"
          type="button"
          class="workflow-agent"
          :class="{ active: isActive(agent.nodes) }"
          @click="selectedNodeId = agent.id"
        >
          <span class="workflow-agent-number">{{ agent.number }}</span>
          <span class="workflow-agent-copy">
            <small>{{ agent.role }}</small>
            <strong>{{ agent.title }}</strong>
            <em>{{ agent.summary }}</em>
          </span>
          <span class="workflow-agent-status">{{ isActive(agent.nodes) ? 'Working' : agent.status }}</span>
        </button>
      </section>

      <div class="workflow-main-route" :aria-label="$t('auto.4e9800a2813b')">
        <template v-for="(step, index) in mainSteps" :key="step.id">
          <button
            type="button"
            class="workflow-step"
            :class="[step.kind, { active: isActive([step.id]) }]"
            @click="selectedNodeId = step.id"
          >
            <span>{{ index + 1 }}</span>
            <strong>{{ step.label }}</strong>
            <small>{{ step.caption }}</small>
          </button>
          <span v-if="index < mainSteps.length - 1" class="workflow-arrow">→</span>
        </template>
      </div>

      <section class="workflow-observation">
        <div class="workflow-fork">
          <span>{{ $t('auto.88ae29519929') }}</span>
          <i></i>
        </div>
        <button
          type="button"
          class="workflow-monitor"
          :class="{ active: isActive(['sensitive_analyzer']) }"
          @click="selectedNodeId = 'sensitive_analyzer'"
        >
          <small>AI WATCH</small>
          <strong>{{ $t('auto.0669f58f0996') }}</strong>
          <span>{{ $t('auto.077f85cc543f') }}</span>
        </button>
        <span class="workflow-plus">+</span>
        <button
          type="button"
          class="workflow-monitor evaluator"
          :class="{ active: isActive(['evaluator']) }"
          @click="selectedNodeId = 'evaluator'"
        >
          <small>{{ $t('auto.c9425dfb8f90') }}</small>
          <strong>{{ $t('auto.9059583833a6') }}</strong>
          <span>{{ $t('auto.ad72e12c59fe') }}</span>
        </button>
        <span class="workflow-arrow">→</span>
        <button
          type="button"
          class="workflow-router"
          :class="{ active: isActive(['router']) }"
          @click="selectedNodeId = 'router'"
        >
          <small>{{ $t('auto.eddc826b311e') }}</small>
          <strong>{{ $t('auto.6dcf16e1c5d3') }}</strong>
          <span>{{ currentRoute || $t('auto.c2fcc0cae82b') }}</span>
        </button>
      </section>

      <section class="workflow-routes">
        <span class="continue"><b>{{ $t('auto.80a6fa1b3607') }}</b> {{ $t('auto.298ee9608e1f') }}</span>
        <span class="replan"><b>{{ $t('auto.9688fe26dfc6') }}</b> {{ $t('auto.fa3f89094159') }}</span>
        <span class="success"><b>{{ $t('auto.eb68c5422955') }}</b> {{ $t('auto.4f99d8588029') }}</span>
        <span class="stop"><b>{{ $t('auto.e64f656cb2eb') }}</b> {{ $t('auto.2dcc4587c2a2') }}</span>
        <span class="pause"><b>{{ $t('auto.781961bc81c2') }}</b> {{ $t('auto.88121cd0887e') }}</span>
      </section>
    </div>
    <n-empty v-else :description="$t('auto.ffbc0276c17c')" />

    <aside v-if="selectedNode" class="workflow-detail">
      <span :style="{ background: selectedNode.color }"></span>
      <div>
        <small>{{ selectedNode.kind }} · {{ selectedNode.id }}</small>
        <strong>{{ selectedNode.label }}</strong>
        <p>{{ selectedNode.description }}</p>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { translateSource } from '../../i18n'

import { computed, ref, watch } from 'vue'
import type { WorkflowDefinition } from '../../api/taskAgents'

const props = defineProps<{
  definition: WorkflowDefinition | null
  currentNode?: string | null
  currentRoute?: string | null
}>()

const selectedNodeId = ref('planner')

const nodeById = computed(() =>
  Object.fromEntries((props.definition?.nodes || []).map((node) => [node.id, node])),
)

const mainSteps = computed(() =>
  [
    { id: 'initialize', caption: 'Restore state', kind: 'system' },
    { id: 'planner', caption: 'Choose next probe', kind: 'agent' },
    { id: 'skill_loader', caption: 'Load selected Skills', kind: 'skill' },
    { id: 'skill_composer', caption: 'Compose Techniques', kind: 'skill' },
    { id: 'executor', caption: 'Write one message', kind: 'agent' },
    { id: 'target', caption: 'Send directly', kind: 'target' },
  ].map((step) => ({
    ...step,
    label: nodeById.value[step.id]?.label || step.id,
  })),
)

const agentCards = [
  {
    id: 'planner',
    number: '01',
    role: 'PLANNING AGENT',
    title: 'Planner',
    summary: 'Selects one PRIMARY and optional SUPPORTING Skills from Technique metadata.',
    status: 'Plans',
    nodes: ['planner', 'skill_loader', 'skill_composer'],
  },
  {
    id: 'executor',
    number: '02',
    role: 'EXECUTION AGENT',
    title: 'Executor',
    summary: 'Applies one PRIMARY Technique and at most one supporting variation per message.',
    status: 'Executes',
    nodes: ['executor', 'target'],
  },
  {
    id: 'evaluator',
    number: '03',
    role: 'EVALUATION AGENT',
    title: translateSource('auto.9059583833a6'),
    summary: 'Evaluates only recorded evidence and recommends the next route.',
    status: 'Evaluates',
    nodes: ['evaluator', 'router'],
  },
]

function isActive(nodeIds: string[]) {
  if (props.currentNode === 'analysis_parallel') {
    return nodeIds.some((id) => ['sensitive_analyzer', 'evaluator'].includes(id))
  }
  return nodeIds.includes(props.currentNode || '')
}

const selectedNode = computed(() => nodeById.value[selectedNodeId.value] || null)
const activeLabel = computed(() => {
  if (props.currentNode === 'analysis_parallel') return 'Parallel observation'
  return nodeById.value[props.currentNode || '']?.label || props.currentNode || 'Ready'
})

watch(
  () => props.currentNode,
  (value) => {
    if (value && value !== 'analysis_parallel') selectedNodeId.value = value
  },
  { immediate: true },
)
</script>

<style scoped>
.workflow-shell { display: grid; gap: 14px; min-height: 0; }
.workflow-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.workflow-heading > div { display: grid; gap: 3px; }
.workflow-heading strong { color: #172033; font-size: 15px; }
.workflow-heading small { color: #718096; }
.workflow-live { display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px; color: #5b21b6; font-size: 11px; font-weight: 800; background: #f5f3ff; border: 1px solid #ddd6fe; border-radius: 999px; }
.workflow-live i { width: 7px; height: 7px; background: #22c55e; border-radius: 50%; box-shadow: 0 0 0 4px rgba(34,197,94,.12); }
.workflow-board { display: grid; gap: 18px; padding: 18px; overflow: auto; background: radial-gradient(circle at 15% 0, rgba(124,58,237,.08), transparent 30%), linear-gradient(145deg,#fbfcff,#f7faff); border: 1px solid rgba(148,163,184,.25); border-radius: 18px; }
.workflow-agent-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.workflow-agent { position: relative; display: grid; grid-template-columns: 42px minmax(0,1fr); gap: 10px; min-height: 112px; padding: 14px; text-align: left; color: inherit; cursor: pointer; background: rgba(255,255,255,.86); border: 1px solid #e5e7eb; border-radius: 16px; box-shadow: 0 8px 25px rgba(30,41,59,.06); transition: .18s ease; }
.workflow-agent:hover,.workflow-agent.active { border-color: #a78bfa; transform: translateY(-2px); box-shadow: 0 12px 30px rgba(109,40,217,.13); }
.workflow-agent.active { background: linear-gradient(145deg,#faf7ff,#f3f8ff); box-shadow: inset 0 0 0 1px rgba(124,58,237,.15),0 12px 30px rgba(109,40,217,.13); }
.workflow-agent-number { display: grid; width: 38px; height: 38px; place-items: center; color: #fff; font-weight: 900; background: linear-gradient(135deg,#8b5cf6,#4f46e5); border-radius: 12px; }
.workflow-agent-copy { display: grid; gap: 3px; }
.workflow-agent-copy small { color: #7c3aed; font-size: 9px; font-weight: 900; letter-spacing: .08em; }
.workflow-agent-copy strong { color: #172033; font-size: 15px; }
.workflow-agent-copy em { color: #64748b; font-size: 11px; font-style: normal; line-height: 1.4; }
.workflow-agent-status { position: absolute; right: 12px; top: 12px; color: #7c3aed; font-size: 9px; font-weight: 800; }
.workflow-main-route { display: flex; align-items: stretch; justify-content: center; gap: 7px; min-width: 870px; }
.workflow-arrow { display: grid; place-items: center; color: #94a3b8; font-size: 18px; }
.workflow-step { display: grid; min-width: 118px; gap: 3px; padding: 10px; text-align: left; color: inherit; cursor: pointer; background: #fff; border: 1px solid #e2e8f0; border-radius: 13px; }
.workflow-step > span { display: grid; width: 21px; height: 21px; place-items: center; color: #64748b; font-size: 9px; background: #f1f5f9; border-radius: 7px; }
.workflow-step strong { color: #263247; font-size: 11px; }
.workflow-step small { color: #7b8799; font-size: 9px; }
.workflow-step.active { border-color: #8b5cf6; background: #faf7ff; box-shadow: 0 0 0 3px rgba(139,92,246,.11); }
.workflow-step.safety { border-left: 4px solid #f97316; }
.workflow-step.agent { border-left: 4px solid #8b5cf6; }
.workflow-step.skill { border-left: 4px solid #3b82f6; }
.workflow-step.target { border-left: 4px solid #0ea5e9; }
.workflow-observation { display: flex; align-items: stretch; justify-content: center; gap: 9px; min-width: 850px; }
.workflow-fork { display: grid; place-items: center; min-width: 90px; color: #64748b; font-size: 10px; font-weight: 800; }
.workflow-fork i { width: 72px; height: 2px; background: linear-gradient(90deg,#38bdf8,#8b5cf6); }
.workflow-monitor,.workflow-router { display: grid; min-width: 190px; gap: 3px; padding: 12px 14px; text-align: left; color: inherit; cursor: pointer; background: #fff; border: 1px solid #dbe5ee; border-radius: 14px; }
.workflow-monitor small,.workflow-router small { color: #16a34a; font-size: 9px; font-weight: 900; letter-spacing: .07em; }
.workflow-monitor strong,.workflow-router strong { color: #1f2937; font-size: 12px; }
.workflow-monitor span,.workflow-router span { color: #64748b; font-size: 10px; line-height: 1.4; }
.workflow-monitor.active,.workflow-router.active { border-color: #22c55e; background: #f5fff8; box-shadow: 0 0 0 3px rgba(34,197,94,.1); }
.workflow-monitor.evaluator small { color: #7c3aed; }
.workflow-plus { display: grid; place-items: center; color: #7c3aed; font-size: 20px; font-weight: 300; }
.workflow-router { border-color: #c4b5fd; }
.workflow-router small { color: #7c3aed; }
.workflow-routes { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.workflow-routes span { padding: 6px 9px; color: #64748b; font-size: 9px; background: #fff; border: 1px solid #e2e8f0; border-radius: 999px; }
.workflow-routes .success b { color: #15803d; }
.workflow-routes .stop b { color: #dc2626; }
.workflow-routes .replan b,.workflow-routes .continue b { color: #6d28d9; }
.workflow-detail { display: flex; gap: 11px; padding: 12px 14px; background: rgba(255,255,255,.8); border: 1px solid rgba(148,163,184,.23); border-radius: 14px; }
.workflow-detail > span { width: 5px; border-radius: 99px; }
.workflow-detail div { display: grid; gap: 2px; }
.workflow-detail small { color: #7c3aed; font-size: 9px; font-weight: 800; text-transform: uppercase; }
.workflow-detail strong { color: #263247; }
.workflow-detail p { margin: 2px 0 0; color: #64748b; font-size: 11px; }
@media (max-width: 900px) {
  .workflow-agent-row { grid-template-columns: 1fr; }
  .workflow-heading { align-items: flex-start; flex-direction: column; }
}
</style>
