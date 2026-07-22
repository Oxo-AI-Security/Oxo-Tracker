<template>
  <div class="agent-review-shell" :class="{ 'agent-review-shell--thinking': isReviewThinking }">
    <GlassPanel class="agent-review-panel">
      <div class="section-heading agent-review-heading">
        <div>
          <p class="eyebrow">Agent design audit</p>
          <h2>Agent Security Review</h2>
          <p class="agent-review-subtitle">
            Review agent design materials, complete asset coverage, then generate interactive function and risk maps.
          </p>
        </div>
        <div class="endpoint-heading-actions">
          <n-button v-if="project" secondary round @click="closeProject">Back to Projects</n-button>
          <n-button secondary round @click="loadProjects">Refresh</n-button>
          <n-button v-if="!project" type="primary" round @click="openProjectSetup()">
            <template #icon><n-icon><AddOutline /></n-icon></template>
            Create Project
          </n-button>
        </div>
      </div>

      <n-alert v-if="error" type="error" closable class="agent-review-alert" @close="error = ''">
        {{ error }}
        <template #action>
          <n-button v-if="project && isErrorStatus(project.status)" size="small" secondary @click="startFunctionReview">Retry Asset Review</n-button>
          <n-button v-else size="small" secondary @click="retryLastAction">Retry</n-button>
        </template>
      </n-alert>

      <section v-if="!project" class="agent-review-projects-page">
        <div class="agent-review-project-library">
          <div class="agent-review-projects-title">
            <div>
              <p class="eyebrow">Projects</p>
              <h3>Review Projects</h3>
              <span>{{ projects.length }} saved review projects</span>
            </div>
          </div>
          <div v-if="projects.length" class="agent-review-option-grid">
            <button v-for="item in projects" :key="item.projectId" type="button" class="agent-review-option-card" @click="selectProject(item.projectId)">
              <span class="agent-review-option-icon">{{ projectInitial(item.projectName) }}</span>
              <span class="agent-review-option-copy">
                <strong>{{ item.projectName }}</strong>
                <small>{{ projectCardDescription(item) }}</small>
              </span>
              <span class="agent-review-option-type">{{ item.agentType }}</span>
              <span class="agent-review-option-status" :class="{ running: isProjectBusy(item) }">
                <n-spin v-if="isProjectBusy(item)" size="small" />
                {{ projectStatusLabel(item.status) }}
              </span>
              <span class="agent-review-option-time">{{ formatTime(item.updatedAt || item.createdAt || '') }}</span>
            </button>
          </div>
          <n-empty v-else description="No review projects yet">
            <template #extra>
              <n-button type="primary" round @click="openProjectSetup()">Create First Project</n-button>
            </template>
          </n-empty>
        </div>
      </section>

      <div v-else class="agent-review-detail-page" :class="{ thinking: isReviewThinking }">
        <div v-if="isReviewThinking" class="agent-review-thinking-canvas" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>

        <div class="agent-review-project-topbar agent-review-project-summary" :class="{ thinking: isReviewThinking }">
          <div>
            <strong>{{ project.projectName }}</strong>
            <span>{{ project.agentType }}</span>
            <div v-if="isReviewThinking" class="agent-review-thinking-status" role="status" aria-live="polite">
              <span class="agent-review-thinking-mark">
                <i />
                <i />
                <i />
              </span>
              <span class="agent-review-thinking-copy">
                <strong>{{ reviewThinkingTitle }}</strong>
                <small>{{ reviewThinkingDetail }}</small>
              </span>
              <span class="agent-review-thinking-bars" aria-hidden="true">
                <i />
                <i />
                <i />
                <i />
              </span>
            </div>
            <span v-else class="agent-review-status-pill" :class="{ running: isBusyStatus(project.status), error: isErrorStatus(project.status) }">
              <n-spin v-if="isBusyStatus(project.status)" size="small" />
              {{ projectStatusLabel(project.status) }}
            </span>
          </div>
          <div class="agent-review-project-topbar-actions">
            <n-button secondary round @click="openProjectSetup(project)">Project Setup</n-button>
            <n-popconfirm positive-text="Delete" negative-text="Cancel" @positive-click="deleteCurrentProject">
              <template #trigger>
                <n-button secondary round type="error">Delete Project</n-button>
              </template>
              Delete this review project and all saved materials?
            </n-popconfirm>
          </div>
        </div>

        <main class="agent-review-main">
          <div class="agent-review-intake-grid">
          <section class="agent-review-card agent-review-upload-card">
            <div class="agent-review-card-head">
              <div>
                <strong>Material Upload</strong>
                <small>Documents, diagrams, prompts, tool specs, RAG notes, and screenshots.</small>
              </div>
              <div class="agent-review-upload-actions">
                <n-select v-model:value="uploadTag" class="agent-review-tag-select" :options="tagOptions" />
                <n-button v-if="project?.materials?.length" secondary round @click="openFilePicker">Upload Files</n-button>
              </div>
            </div>
            <input
              ref="fileInputRef"
              class="agent-review-file-input"
              type="file"
              multiple
              accept=".doc,.docx,.xls,.xlsx,.csv,.pdf,.txt,.md,.json,.yaml,.yml,.png,.jpg,.jpeg,.webp"
              @change="handleFileInput"
            />
            <div
              v-if="!project?.materials?.length"
              class="agent-review-dropzone"
              :class="{ dragging: dragging }"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="handleDrop"
            >
              <n-icon size="30"><CloudUploadOutline /></n-icon>
              <strong>Drop files here</strong>
              <span>.doc, .docx, .xls, .xlsx, .csv, .pdf, .txt, .md, .json, .yaml, .png, .jpg, .webp</span>
              <n-button secondary round @click="openFilePicker">Choose Files</n-button>
            </div>

            <div v-if="project?.materials?.length" class="agent-review-file-list">
              <article v-for="file in filteredMaterials" :key="file.fileId" class="agent-review-file">
                <div>
                  <button type="button" class="agent-review-file-name" @click="openMaterial(file)">
                    {{ file.fileName }}
                  </button>
                  <small>{{ file.extension || file.contentType || 'file' }} / {{ formatBytes(file.size) }} / {{ formatTime(file.uploadedAt) }}</small>
                  <em v-if="isImageMaterial(file)">{{ materialVisualNote }}</em>
                  <em v-else-if="!file.extractionSupported">This file was uploaded successfully, but text extraction is not fully supported yet.</em>
                </div>
                <n-tag size="small">{{ file.tag }}</n-tag>
                <n-button quaternary circle size="small" @click="deleteMaterial(file.fileId)">
                  <template #icon><n-icon><TrashOutline /></n-icon></template>
                </n-button>
              </article>
              <n-empty v-if="!filteredMaterials.length" description="No files under this material type" />
            </div>
          </section>

          <section class="agent-review-card agent-review-manual-card">
            <div class="agent-review-card-head">
              <div>
                <strong>Manual Inputs</strong>
                <small>Paste long prompts, tool specs, RAG sources and endpoint notes in focused editors.</small>
              </div>
              <n-button secondary round :disabled="!project" @click="saveManualContext">Save Inputs</n-button>
            </div>
            <div class="agent-review-manual-grid compact">
              <button
                v-for="item in manualInputCards"
                :key="item.key"
                type="button"
                class="agent-review-input-card"
                :class="{ filled: Boolean(manualInputs[item.key]) }"
                @click="openManualEditor(item.key)"
              >
                <span>{{ item.label }}</span>
                <strong>{{ manualInputStatus(item.key) }}</strong>
                <small>{{ manualPreview(manualInputs[item.key], item.placeholder) }}</small>
              </button>
            </div>
          </section>
          </div>

          <section v-if="missingQuestions.length" class="agent-review-card agent-review-missing-workflow" :class="{ collapsed: missingPanelCollapsed }">
            <div class="agent-review-card-head">
              <div>
                <strong>Supplemental Information</strong>
                <small>Round 1 identifies missing facts. Answer these questions, then run Update Asset Review to continue the inventory conversation.</small>
              </div>
              <div class="agent-review-missing-head-actions">
                <n-button secondary round @click="missingPanelCollapsed = !missingPanelCollapsed">
                  {{ missingPanelCollapsed ? 'Expand' : 'Collapse' }}
                </n-button>
                <n-button type="primary" round :loading="reviewing" :disabled="hasUnansweredMissingQuestions" @click="generateAssetGraph">
                  Generate Asset Graph
                </n-button>
              </div>
            </div>
            <div v-show="!missingPanelCollapsed" class="agent-review-missing-list">
              <article v-for="group in missingQuestionGroups" :key="group.dimension.dimension_id" class="agent-review-missing-group">
                <header>
                  <span>{{ group.dimension.dimension_id }}</span>
                  <strong>{{ group.dimension.dimension_name }}</strong>
                </header>
                <div
                  v-for="item in group.questions"
                  :key="item.id"
                  class="agent-review-missing"
                  :class="{ answered: Boolean(missingAnswers[item.id]), locked: missingAnswerLocks[item.id] }"
                >
                  <div class="agent-review-missing-title">
                    <div class="agent-review-missing-question-copy">
                      <n-tag size="small" :type="missingPriorityType(item.priority)">{{ item.priority }}</n-tag>
                      <strong>{{ item.question }}</strong>
                    </div>
                    <div class="agent-review-missing-question-actions">
                      <n-popconfirm
                        positive-text="Set None"
                        negative-text="Cancel"
                        @positive-click="cancelMissingAnswer(item.id)"
                      >
                        <template #trigger>
                          <n-button size="small" secondary round>None</n-button>
                        </template>
                        Mark this item as none / not applicable?
                      </n-popconfirm>
                      <n-button size="small" secondary round @click="toggleMissingAnswerLock(item.id)">
                        {{ missingAnswerLocks[item.id] ? 'Edit' : 'Save' }}
                      </n-button>
                    </div>
                  </div>
                <small>{{ item.reason }}</small>
                  <n-input
                    v-model:value="missingAnswers[item.id]"
                    type="textarea"
                    :autosize="{ minRows: 2, maxRows: 5 }"
                    :readonly="Boolean(missingAnswerLocks[item.id])"
                    :class="{ locked: missingAnswerLocks[item.id], answered: missingAnswers[item.id] }"
                    placeholder="Answer"
                    @blur="lockMissingAnswer(item.id)"
                    @dblclick="unlockMissingAnswer(item.id)"
                  />
                  <small v-if="missingAnswerLocks[item.id]" class="agent-review-lock-note">Saved and locked. Double-click the input or click Edit to update.</small>
                </div>
              </article>
            </div>
            <n-alert v-if="hasUnansweredMissingQuestions" type="warning" class="agent-review-alert">
              Answer every supplemental question before generating the architecture graph.
            </n-alert>
          </section>

          <section class="agent-review-card agent-review-workspace-card">
            <div class="agent-review-workspace-head unified">
              <div>
                <p class="eyebrow">Asset review workflow</p>
                <strong>{{ activeMap === 'risk' ? 'Risk Overlay Map' : 'Function Review Map' }}</strong>
                <small>{{ project?.functionReview?.summary || 'Start with asset coverage. Risk analysis starts only after critical supplemental information is answered.' }}</small>
                <div v-if="activeMap !== 'risk' && assetCompleteness" class="agent-review-graph-metrics">
                  <span>Completeness {{ Math.round(assetCompleteness.score) }}%</span>
                  <span>{{ assetCompleteness.status }}</span>
                  <span>{{ assetMissingCount }} missing signals</span>
                </div>
              </div>
              <div class="agent-review-risk-toolbar">
                <n-button secondary round :disabled="activeMap === 'function' && !project?.functionReview" @click="activeMap = activeMap === 'risk' ? 'function' : 'risk'">
                  {{ activeMap === 'risk' ? 'Function Map' : 'Risk Map' }}
                </n-button>
                <n-button secondary round :disabled="!hasRenderableGraph" @click="autoLayout">Auto Layout</n-button>
                <n-button v-if="activeMap === 'function'" secondary round :disabled="!hasRenderableGraph" @click="saveFunctionMap">Save Layout</n-button>
                <n-select v-if="activeMap === 'risk'" v-model:value="riskFilter" class="agent-review-filter-select" :options="riskFilterOptions" />
                <n-button v-if="activeMap === 'risk' && isCurrentRiskReviewing" secondary round type="warning" @click="cancelCurrentReview">
                  Cancel
                </n-button>
                <n-button v-if="activeMap === 'risk'" class="red-test-button" round :loading="isCurrentRiskReviewing" :disabled="!canGenerateRiskMap || isCurrentRiskReviewing" @click="generateRiskMap">
                  Generate Risk Map
                </n-button>
                <n-button v-else-if="isCurrentFunctionReviewing" secondary round type="warning" @click="cancelCurrentReview">
                  Cancel
                </n-button>
                <n-button v-else-if="canGenerateAssetGraph" type="primary" round :loading="reviewing" @click="generateAssetGraph">
                  Generate Asset Graph
                </n-button>
                <n-button v-else type="primary" round :loading="isCurrentFunctionReviewing" :disabled="!project || isCurrentFunctionReviewing" @click="startFunctionReview">
                  Start Asset Review
                </n-button>
              </div>
            </div>

            <section v-if="activeMap === 'risk'" class="agent-review-risk-overview">
              <div class="agent-review-feature-inventory-head">
                <div>
                  <strong>Risk & Details</strong>
                </div>
                <span>{{ filteredRisks.length }} risks</span>
              </div>
              <div v-if="project?.riskReview?.risks?.length" class="agent-review-risk-grid">
                <button
                  v-for="risk in filteredRisks"
                  :key="risk.id"
                  type="button"
                  class="agent-review-risk-card"
                  :class="[{ active: highlightedRiskId === risk.id }, risk.severity]"
                  @click="highlightRisk(risk.id)"
                >
                  <span :class="risk.severity">{{ risk.severity }}</span>
                  <strong>{{ risk.title }}</strong>
                </button>
              </div>
              <div v-else class="agent-review-risk-prompt">
                <strong>Risk map is not generated yet</strong>
                <span>Add optional risk focus notes below, then generate the risk overlay.</span>
              </div>
            </section>

            <section v-else-if="project?.functionReview && assetInventoryReady" class="agent-review-asset-matrix">
              <div class="agent-review-feature-inventory-head">
                <div>
                  <strong>AI Agent Asset Inventory</strong>
                  <small>Round 2 inventory output. Fixed 12-dimension asset model before capability and risk mapping.</small>
                </div>
                <span>{{ coverageRows.filter(dimensionHasAssets).length }} / 12 present</span>
              </div>
              <div class="agent-review-asset-grid">
                <button
                  v-for="dimension in coverageRows"
                  :key="dimension.dimension_id"
                  type="button"
                  class="agent-review-asset-card"
                  :class="[{ present: dimensionHasAssets(dimension), empty: !dimensionHasAssets(dimension), active: selectedDimensionId === dimension.dimension_id }]"
                  @click="openDimensionDetail(dimension.dimension_id)"
                >
                  <div class="agent-review-asset-card-top">
                    <span>{{ dimension.dimension_id }}</span>
                    <b>{{ dimensionAssetStatusLabel(dimension) }}</b>
                  </div>
                  <div class="agent-review-asset-card-title">
                    <strong>{{ dimension.dimension_name }}</strong>
                    <small>{{ dimension.dimension_zh_name }}</small>
                  </div>
                  <div v-if="dimensionHasAssets(dimension)" class="agent-review-asset-chip-list">
                    <span v-for="asset in dimensionAssetNames(dimension)" :key="asset">{{ asset }}</span>
                  </div>
                  <p v-else>No confirmed asset in uploaded materials.</p>
                </button>
              </div>
            </section>

            <section v-else-if="project?.functionReview && !hasGeneratedAssetGraph" class="agent-review-asset-waiting">
              <n-empty :description="hasUnansweredMissingQuestions ? 'Answer all supplemental questions before generating the architecture graph' : 'Questions are complete. Generate Asset Graph to build the layered component map.'">
                <template #extra>
                  <n-button v-if="canGenerateAssetGraph" type="primary" round @click="generateAssetGraph">Generate Asset Graph</n-button>
                </template>
              </n-empty>
            </section>

            <section v-if="activeMap !== 'risk' && hasGeneratedAssetGraph && featureRows.length" class="agent-review-feature-inventory">
              <div class="agent-review-feature-inventory-head">
                <div>
                  <strong>Capability Inventory</strong>
                  <small>Click a capability to inspect trigger, inputs, outputs, dependencies, tools, RAG and next steps.</small>
                </div>
                <span>{{ featureRows.length }} extracted features</span>
              </div>
              <div class="agent-review-feature-grid">
                <button v-for="feature in featureRows" :key="feature.id" type="button" class="agent-review-feature-card" @click="openFeatureDetail(feature)">
                  <span>{{ feature.id }}</span>
                  <strong>{{ feature.name }}</strong>
                  <p>{{ feature.description }}</p>
                  <small>{{ formatMappedDimensions(feature.mapped_dimensions) }}</small>
                  <small>{{ feature.trigger || 'No trigger captured' }}</small>
                </button>
              </div>
            </section>

            <div v-if="hasGeneratedAssetGraph || activeMap === 'risk'" class="agent-review-map-layout unified" :class="{ risk: activeMap === 'risk' }">
              <div class="agent-review-flow-wrap">
                <VueFlow
                  v-if="hasRenderableGraph"
                  :key="activeMap"
                  v-model:nodes="visibleNodes"
                  v-model:edges="visibleEdges"
                  fit-view-on-init
                  :min-zoom="0.35"
                  :max-zoom="1.8"
                  :default-viewport="{ x: 24, y: 60, zoom: activeMap === 'risk' ? 0.72 : 0.85 }"
                  class="agent-review-flow"
                  @node-click="onNodeClick"
                  @edge-click="onEdgeClick"
                  @node-drag-stop="markMapEdited"
                >
                  <Background pattern-color="#3f3f46" bg-color="#171717" :gap="18" :size="1.15" />
                  <Controls class="agent-review-flow-controls" />
                  <template #node-asset="{ data }">
                    <AssetNode :data="data" />
                  </template>
                  <template #node-custom="{ data }">
                    <div class="agent-review-flow-node" :class="[`type-${normalizeType(data.nodeType)}`, `risk-${data.riskSeverity || 'none'}`]">
                      <Handle type="target" :position="Position.Left" />
                      <div class="agent-review-flow-node-icon">{{ data.featureId || nodeIcon(data.nodeType) }}</div>
                      <div class="agent-review-flow-node-copy">
                        <span class="agent-review-node-badge">{{ displayNodeType(data.nodeType) }}</span>
                        <strong>{{ data.label }}</strong>
                        <small>{{ data.description }}</small>
                      </div>
                      <b v-if="data.riskSeverity">{{ data.riskSeverity }}</b>
                      <Handle type="source" :position="Position.Right" />
                    </div>
                  </template>
                </VueFlow>
                <div v-else-if="isGraphReviewing" class="agent-review-ai-loading">
                  <span />
                  <strong>{{ activeMap === 'risk' ? 'Generating risk overlay' : assetReviewPhaseTitle }}</strong>
                  <small>{{ activeMap === 'risk' ? 'Mapping signals, edges, and context into a structured graph...' : assetReviewPhaseDetail }}</small>
                </div>
                <n-empty v-else :description="activeMap === 'risk' ? 'Generate Risk Map to render the risk overlay' : 'Run Asset Review to generate the capability flow map'" />
              </div>

              <aside class="agent-review-detail">
                <div class="agent-review-card-head">
                  <strong>{{ activeMap === 'risk' ? 'Selected Risk Context' : 'Details' }}</strong>
                  <div v-if="activeMap !== 'risk'" class="agent-review-actions">
                    <n-button size="small" secondary @click="openNodeEditor()">Add Node</n-button>
                    <n-button size="small" secondary @click="openEdgeEditor()">Add Edge</n-button>
                  </div>
                </div>
                <template v-if="activeMap === 'risk'">
                  <div v-if="selectedRisk" class="agent-review-risk-detail-card" :class="selectedRisk.severity">
                    <span :class="selectedRisk.severity">{{ selectedRisk.severity }}</span>
                    <h3>{{ selectedRisk.title }}</h3>
                    <small>{{ selectedRisk.category }}</small>
                    <dl>
                      <div><dt>Description</dt><dd>{{ selectedRisk.description }}</dd></div>
                      <div><dt>Impact</dt><dd>{{ selectedRisk.impact }}</dd></div>
                      <div><dt>Recommendation</dt><dd>{{ selectedRisk.recommendation }}</dd></div>
                    </dl>
                  </div>
                  <div v-else-if="activeRisks.length" class="agent-review-risk-accordion">
                    <button
                      v-for="risk in activeRisks"
                      :key="risk.id"
                      type="button"
                      class="agent-review-risk-accordion-row"
                      :class="{ active: highlightedRiskId === risk.id }"
                      @click="highlightRisk(risk.id)"
                    >
                      <span :class="risk.severity">{{ risk.severity }}</span>
                      <strong>{{ risk.title }}</strong>
                    </button>
                  </div>
                  <div v-else class="agent-review-detail-empty">
                    <n-empty description="Select a risk or a node with risks" />
                  </div>
                </template>
                <template v-else-if="selectedElement">
                  <div v-if="selectedAssetDetail" class="agent-review-asset-inspector">
                    <span :class="selectedAssetDetail.status">{{ selectedAssetDetail.status }}</span>
                    <h3>{{ selectedAssetDetail.name }}</h3>
                    <small>{{ selectedAssetDetail.asset_type }} / {{ selectedAssetDetail.layer }}</small>
                    <dl>
                      <div><dt>Description</dt><dd>{{ selectedAssetDetail.description || '-' }}</dd></div>
                      <div><dt>Evidence</dt><dd>{{ formatList(selectedAssetDetail.source_evidence) }}</dd></div>
                      <div><dt>Data</dt><dd>{{ formatList(selectedAssetDetail.data_handled) }}</dd></div>
                      <div><dt>Permissions</dt><dd>{{ formatList(selectedAssetDetail.permissions) }}</dd></div>
                      <div><dt>Access</dt><dd>{{ selectedAssetDetail.access_mode || '-' }}</dd></div>
                      <div><dt>Approval</dt><dd>{{ selectedAssetDetail.requires_approval ? 'Required' : 'Not captured' }}</dd></div>
                      <div><dt>Risk Hint</dt><dd>{{ selectedAssetDetail.risk_hint || '-' }}</dd></div>
                      <div><dt>Metadata</dt><dd>{{ formatStructured(selectedAssetDetail.metadata) }}</dd></div>
                    </dl>
                  </div>
                  <div v-else-if="selectedRelationshipDetail" class="agent-review-asset-inspector">
                    <span>{{ selectedRelationshipDetail.edge_type }}</span>
                    <h3>{{ selectedRelationshipDetail.label || selectedRelationshipDetail.id }}</h3>
                    <small>{{ selectedRelationshipDetail.source }} -> {{ selectedRelationshipDetail.target }}</small>
                    <dl>
                      <div><dt>Description</dt><dd>{{ selectedRelationshipDetail.description || '-' }}</dd></div>
                      <div><dt>Data Flow</dt><dd>{{ formatList(selectedRelationshipDetail.data_flow) }}</dd></div>
                      <div><dt>Auth</dt><dd>{{ selectedRelationshipDetail.auth_context || '-' }}</dd></div>
                      <div><dt>Status</dt><dd>{{ selectedRelationshipDetail.status || '-' }}</dd></div>
                    </dl>
                  </div>
                  <n-form v-else label-placement="top">
                    <n-form-item label="Name / Label">
                      <n-input v-model:value="detailDraft.label" />
                    </n-form-item>
                    <n-form-item label="Type">
                      <n-select v-if="selectedElement.kind === 'node'" v-model:value="detailDraft.nodeType" :options="nodeTypeOptions" />
                      <n-input v-else v-model:value="detailDraft.flowType" />
                    </n-form-item>
                    <n-form-item label="Description">
                      <n-input v-model:value="detailDraft.description" type="textarea" :autosize="{ minRows: 4, maxRows: 8 }" />
                    </n-form-item>
                  </n-form>
                  <div class="agent-review-actions">
                    <n-button secondary round @click="applyDetailEdit">Save</n-button>
                    <n-button secondary round type="error" @click="deleteSelected">Delete</n-button>
                  </div>
                </template>
                <div v-else class="agent-review-detail-empty">
                  <div v-if="isGraphReviewing" class="agent-review-ai-loading compact">
                    <span />
                    <strong>Preparing context</strong>
                    <small>Details will appear after the review finishes.</small>
                  </div>
                  <n-empty v-else description="Select a node or edge to inspect" />
                </div>
              </aside>
            </div>
          </section>

          <n-alert v-if="activeMap === 'risk' && !canGenerateRiskMap" type="warning" class="agent-review-alert">
            Risk Map is not ready. Please answer critical supplemental information first.
            <div v-if="riskReadinessIssues.length" class="agent-review-readiness-list">
              <span v-for="issue in riskReadinessIssues" :key="issue">{{ issue }}</span>
            </div>
          </n-alert>

          <section v-if="activeMap === 'risk'" class="agent-review-card">
            <div class="agent-review-card-head">
              <div>
                <strong>Additional Risk Focus</strong>
                <small>Add extra risk points or assumptions, then regenerate the risk overlay.</small>
              </div>
              <n-button type="primary" round :loading="isCurrentRiskReviewing" :disabled="!canGenerateRiskMap" @click="generateRiskMap">
                Regenerate Risk Map
              </n-button>
            </div>
            <n-input
              v-model:value="additionalRiskNotes"
              type="textarea"
              :autosize="{ minRows: 3, maxRows: 6 }"
              placeholder="Example: focus on tenant isolation, data exfiltration paths, parser sandboxing, or approval controls."
            />
          </section>

        </main>
      </div>
    </GlassPanel>

    <n-modal v-model:show="projectSetupOpen" preset="card" title="Project Setup" class="agent-review-setup-modal">
      <n-form label-placement="top" class="agent-review-form">
        <n-form-item label="Project Name">
          <n-input v-model:value="setup.projectName" placeholder="Support Copilot" />
        </n-form-item>
        <n-form-item label="Description">
          <n-input v-model:value="setup.description" type="textarea" :autosize="{ minRows: 3, maxRows: 5 }" />
        </n-form-item>
        <n-form-item label="Agent Type">
          <n-select v-model:value="setup.agentType" :options="agentTypeOptions" />
        </n-form-item>
        <n-form-item label="AI Provider">
          <n-select v-model:value="setup.provider" :options="providerOptions" />
        </n-form-item>
        <n-form-item label="Review Model">
          <n-select v-model:value="setup.modelName" :options="modelOptions" />
        </n-form-item>
        <n-alert type="info" class="agent-review-model-note">
          {{ selectedProviderInfo?.supported || 'Select a provider to see supported material formats.' }}
        </n-alert>
        <n-form-item :label="selectedProviderInfo?.apiKeyLabel || 'API Key'">
          <n-input v-model:value="providerApiKey" type="password" show-password-on="click" placeholder="Only used by this module" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="agent-review-actions">
          <n-button secondary round @click="saveProviderKey">Save Key</n-button>
          <n-button secondary round :loading="testingProvider" @click="testProviderConnection">Test Connection</n-button>
          <n-button type="primary" round @click="saveProjectSetup">{{ project ? 'Save Setup' : 'Create Project' }}</n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="manualEditorOpen" preset="card" :title="manualEditorTitle" class="agent-review-manual-modal">
      <n-input
        v-model:value="manualEditorText"
        type="textarea"
        :placeholder="manualEditorPlaceholder"
        :autosize="{ minRows: 14, maxRows: 22 }"
      />
      <template #footer>
        <div class="agent-review-actions">
          <n-button secondary round @click="manualEditorOpen = false">Close</n-button>
          <n-button type="primary" round @click="saveManualFromModal">Save Inputs</n-button>
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="featureDetailOpen" preset="card" :title="selectedFeature?.name || 'Capability Detail'" class="agent-review-feature-modal">
      <div v-if="selectedFeature" class="agent-review-feature-detail">
        <span>{{ selectedFeature.id }}</span>
        <p>{{ selectedFeature.description }}</p>
        <dl>
          <div><dt>Mapped Dimensions</dt><dd>{{ formatMappedDimensions(selectedFeature.mapped_dimensions) }}</dd></div>
          <div><dt>Related Assets</dt><dd>{{ formatMappedDimensions(selectedFeature.related_asset_ids) }}</dd></div>
          <div><dt>Status</dt><dd>{{ selectedFeature.status || '-' }}</dd></div>
          <div><dt>Trigger</dt><dd>{{ selectedFeature.trigger || '-' }}</dd></div>
          <div><dt>Inputs</dt><dd>{{ formatList(selectedFeature.inputs) }}</dd></div>
          <div><dt>Outputs</dt><dd>{{ formatList(selectedFeature.outputs) }}</dd></div>
          <div><dt>Components</dt><dd>{{ formatList(selectedFeature.components) }}</dd></div>
          <div><dt>Tools</dt><dd>{{ formatList(selectedFeature.tools) }}</dd></div>
          <div><dt>Data Assets</dt><dd>{{ formatList(selectedFeature.data_assets) }}</dd></div>
          <div><dt>Permissions</dt><dd>{{ formatList(selectedFeature.permissions) }}</dd></div>
          <div><dt>Dependencies</dt><dd>{{ formatList(selectedFeature.dependencies) }}</dd></div>
          <div><dt>RAG</dt><dd>{{ formatStructured(selectedFeature.rag) }}</dd></div>
          <div><dt>File / Image</dt><dd>{{ formatStructured(selectedFeature.file_or_image_processing) }}</dd></div>
          <div><dt>Next</dt><dd>{{ formatList(selectedFeature.flow_next) }}</dd></div>
        </dl>
      </div>
    </n-modal>

    <n-modal v-model:show="dimensionDetailOpen" preset="card" :title="selectedDimension?.dimension_name || 'Asset Dimension Detail'" class="agent-review-dimension-modal">
      <div v-if="selectedDimension" class="agent-review-asset-detail">
        <div class="agent-review-asset-detail-hero" :class="{ empty: !dimensionHasAssets(selectedDimension) }">
          <span>{{ selectedDimension.dimension_id }}</span>
          <div>
            <div class="agent-review-asset-detail-titleline">
              <strong>{{ dimensionAssetStatusLabel(selectedDimension) }}</strong>
              <em>{{ selectedDimension.dimension_zh_name }}</em>
            </div>
            <p>{{ selectedDimension.summary }}</p>
          </div>
        </div>
        <section v-if="selectedDimension.detected_assets.length" class="agent-review-asset-detail-section">
          <header>
            <strong>Detected Assets</strong>
            <small>{{ selectedDimension.detected_assets.length }} found</small>
          </header>
          <div class="agent-review-asset-detail-list">
            <article v-for="asset in selectedDimension.detected_assets" :key="asset.asset_id" class="agent-review-asset-detail-item">
              <div class="agent-review-asset-detail-item-head">
                <div>
                  <strong>{{ asset.name || asset.asset_id }}</strong>
                  <small>{{ asset.description || 'No description captured.' }}</small>
                </div>
                <span>{{ asset.asset_type || 'asset' }}</span>
              </div>
              <dl>
                <div><dt>Risk</dt><dd>{{ asset.risk_level || 'unknown' }}</dd></div>
                <div><dt>Confidence</dt><dd>{{ formatConfidence(asset.confidence) }}</dd></div>
                <div><dt>Source</dt><dd>{{ asset.source_dimension_id || selectedDimension.dimension_id }}</dd></div>
              </dl>
            </article>
          </div>
        </section>
        <section v-else class="agent-review-asset-detail-empty">
          <strong>No asset found for this dimension</strong>
          <p>The uploaded materials did not identify this asset area. It remains gray in the inventory.</p>
        </section>
        <section class="agent-review-asset-detail-section">
          <header>
            <strong>Evidence & Follow-up</strong>
            <small>Source clues and open gaps</small>
          </header>
          <dl class="agent-review-asset-detail-meta">
            <div><dt>Evidence</dt><dd>{{ formatEvidenceItems(selectedDimension.evidence) }}</dd></div>
            <div><dt>Missing Fields</dt><dd>{{ formatList(selectedDimension.missing_fields) }}</dd></div>
            <div><dt>Follow-up Questions</dt><dd>{{ relatedQuestions(selectedDimension.dimension_id).map((item) => item.question).join('\n') || '-' }}</dd></div>
            <div><dt>Risk Hints</dt><dd>{{ formatList(selectedDimension.potential_risk_hints) }}</dd></div>
          </dl>
        </section>
      </div>
    </n-modal>

    <n-modal v-model:show="materialPreviewOpen" preset="card" :title="materialPreviewTitle" class="agent-review-preview-modal">
      <div class="agent-review-preview-shell">
        <div class="agent-review-preview-toolbar">
          <span>{{ materialPreviewMeta }}</span>
          <div v-if="materialPreviewMode === 'image'" class="agent-review-preview-actions">
            <n-button secondary round size="small" @click="zoomPreview(-0.2)">Zoom Out</n-button>
            <n-button secondary round size="small" @click="resetPreviewTransform">Reset</n-button>
            <n-button secondary round size="small" @click="zoomPreview(0.2)">Zoom In</n-button>
          </div>
        </div>
        <div
          v-if="materialPreviewMode === 'image'"
          class="agent-review-image-preview"
          @wheel.prevent="onPreviewWheel"
          @pointerdown="startPreviewDrag"
          @pointermove="movePreviewDrag"
          @pointerup="endPreviewDrag"
          @pointercancel="endPreviewDrag"
          @pointerleave="endPreviewDrag"
        >
          <img
            :src="materialPreviewUrl"
            :alt="materialPreviewTitle"
            :style="{ transform: `translate(${previewPan.x}px, ${previewPan.y}px) scale(${previewZoom})` }"
            draggable="false"
          />
        </div>
        <iframe v-else-if="materialPreviewMode === 'frame'" class="agent-review-frame-preview" :src="materialPreviewUrl" />
        <pre v-else-if="materialPreviewMode === 'text'" class="agent-review-text-preview">{{ materialPreviewText }}</pre>
        <div v-else class="agent-review-preview-fallback">
          <n-empty :description="materialPreviewText || 'Preview is not available for this file.'">
            <template #extra>
              <n-button secondary round @click="openMaterialInNewTab">Open File</n-button>
            </template>
          </n-empty>
        </div>
      </div>
    </n-modal>

    <n-modal v-model:show="nodeEditorOpen" preset="card" title="Node" class="agent-review-modal">
      <n-form label-placement="top">
        <n-form-item label="Name"><n-input v-model:value="nodeDraft.label" /></n-form-item>
        <n-form-item label="Type"><n-select v-model:value="nodeDraft.nodeType" :options="nodeTypeOptions" /></n-form-item>
        <n-form-item label="Description"><n-input v-model:value="nodeDraft.description" type="textarea" /></n-form-item>
      </n-form>
      <template #footer><n-button type="primary" round @click="saveNodeDraft">Save</n-button></template>
    </n-modal>

    <n-modal v-model:show="edgeEditorOpen" preset="card" title="Edge" class="agent-review-modal">
      <n-form label-placement="top">
        <n-form-item label="Source"><n-select v-model:value="edgeDraft.source" :options="nodeSelectOptions" /></n-form-item>
        <n-form-item label="Target"><n-select v-model:value="edgeDraft.target" :options="nodeSelectOptions" /></n-form-item>
        <n-form-item label="Label"><n-input v-model:value="edgeDraft.label" /></n-form-item>
        <n-form-item label="Flow Type"><n-input v-model:value="edgeDraft.flowType" placeholder="Prompt, Tool Call, API Request" /></n-form-item>
        <n-form-item label="Description"><n-input v-model:value="edgeDraft.description" type="textarea" /></n-form-item>
      </n-form>
      <template #footer><n-button type="primary" round @click="saveEdgeDraft">Save</n-button></template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Handle, MarkerType, Position, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import { AddOutline, CloudUploadOutline, TrashOutline } from '@vicons/ionicons5'
import { useMessage } from 'naive-ui'
import GlassPanel from '../../components/GlassPanel.vue'
import AssetNode from '../../modules/agents/agent-security-review/components/AssetNode.vue'
import { normalizeAssetGraph } from '../../modules/agents/agent-security-review/graph/assetGraphNormalizer'
import { assetGraphToVueFlow } from '../../modules/agents/agent-security-review/graph/assetGraphToVueFlow'
import type { AgentAssetGraph, AgentAssetNode, AgentAssetEdge } from '../../modules/agents/agent-security-review/graph/assetGraph.types'
import {
  agentSecurityReviewApi,
  defaultManualInputs,
  type FlowGraph,
  type ManualInputs,
  type ModelProvider,
  type DimensionCoverage,
  type ReviewMaterial,
  type ReviewProject,
} from '../../api/agentSecurityReview'

const message = useMessage()
const route = useRoute()
const projects = ref<ReviewProject[]>([])
const project = ref<ReviewProject | null>(null)
const visibleNodes = ref<any[]>([])
const visibleEdges = ref<any[]>([])
const activeMap = ref<'function' | 'risk'>('function')
const error = ref('')
const lastAction = ref<(() => Promise<void>) | null>(null)
const reviewing = ref(false)
const riskReviewing = ref(false)
const testingProvider = ref(false)
const dragging = ref(false)
const uploadTag = ref('Architecture')
const providerApiKey = ref('')
const modelProviders = ref<Record<string, ModelProvider>>({})
const riskFilter = ref('all')
const highlightedRiskId = ref('')
const projectSetupOpen = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const manualEditorOpen = ref(false)
const manualEditorKey = ref<keyof ManualInputs>('systemPrompt')
const featureDetailOpen = ref(false)
const selectedFeature = ref<any | null>(null)
const selectedDimensionId = ref('D01')
const dimensionDetailOpen = ref(false)
let pollTimer: number | undefined

const setup = reactive({ projectName: '', description: '', agentType: 'RAG Agent', provider: 'gemini', modelName: 'gemini-3.5-flash' })
const manualInputs = reactive<ManualInputs>({ ...defaultManualInputs })
const missingAnswers = reactive<Record<string, string>>({})
const missingAnswerLocks = reactive<Record<string, boolean>>({})
const missingPanelCollapsed = ref(false)
const additionalRiskNotes = ref('')
const selectedElement = ref<{ kind: 'node' | 'edge'; id: string } | null>(null)
const detailDraft = reactive({ label: '', nodeType: '', flowType: '', description: '' })
const nodeEditorOpen = ref(false)
const edgeEditorOpen = ref(false)
const nodeDraft = reactive({ label: '', nodeType: 'Agent Runtime', description: '' })
const edgeDraft = reactive({ source: '', target: '', label: '', flowType: '', description: '' })
const materialPreviewOpen = ref(false)
const materialPreviewFile = ref<ReviewMaterial | null>(null)
const materialPreviewMode = ref<'image' | 'frame' | 'text' | 'fallback'>('fallback')
const materialPreviewUrl = ref('')
const materialPreviewText = ref('')
const previewZoom = ref(1)
const previewPan = reactive({ x: 0, y: 0 })
const previewDrag = reactive({ active: false, startX: 0, startY: 0, panX: 0, panY: 0 })

const agentTypeOptions = ['Chat Agent', 'RAG Agent', 'Tool-Using Agent', 'Multi-Agent System', 'Workflow Agent', 'Other'].map((value) => ({ label: value, value }))
const tagOptions = ['Architecture', 'API Spec', 'Prompt', 'Tool Spec', 'RAG Document', 'Screenshot', 'Permission Design', 'Other'].map((value) => ({ label: value, value }))
const nodeTypeOptions = ['User', 'Input', 'Feature', 'Output', 'Frontend', 'Backend', 'Agent Runtime', 'LLM', 'Prompt', 'Tool Router', 'Tool', 'RAG Retriever', 'Vector DB', 'Database', 'External API', 'File Storage', 'File Parser', 'Authentication', 'Audit Log', 'Human Review'].map((value) => ({ label: value, value }))
const riskFilterOptions = ['all', 'critical', 'high', 'medium', 'low'].map((value) => ({ label: value === 'all' ? 'All Severities' : value[0].toUpperCase() + value.slice(1), value }))
const manualInputCards: Array<{ key: keyof ManualInputs; label: string; placeholder: string }> = [
  { key: 'systemPrompt', label: 'System Prompt', placeholder: 'Paste instruction hierarchy, role rules, constraints and policy text.' },
  { key: 'toolList', label: 'Tool List', placeholder: 'List tools, arguments, permissions, read/write behavior and return values.' },
  { key: 'ragSource', label: 'RAG Source', placeholder: 'Knowledge bases, indexes, retrievers, vector DBs and citation behavior.' },
  { key: 'apiEndpointDescription', label: 'API / Endpoint Description', placeholder: 'External APIs, callbacks, webhooks, auth flows and data contracts.' },
  { key: 'extraNotes', label: 'Extra Notes', placeholder: 'Any additional design detail that helps reconstruct capability flow.' },
]
const assetDimensions: DimensionCoverage[] = [
  createDimension('D01', 'Agent Profile', 'Identity and ownership', 'Agent type, business goals, deployment environment, owner, business criticality, and lifecycle status.'),
  createDimension('D02', 'Identity, Roles & Permission Boundary', 'Authorization boundary', 'User identity, agent identity, service accounts, token scope, delegated identity, tenant boundary, and privilege context.'),
  createDimension('D03', 'Input Surfaces', 'Ingress points', 'Chat, file upload, API input, webhook, scheduled task, URL, email, form, voice, and every surface that can influence the agent.'),
  createDimension('D04', 'Instruction & Prompt System', 'Instruction stack', 'System prompt, developer prompt, prompt templates, tool-use rules, refusal rules, strategy rules, and user-controlled variables.'),
  createDimension('D05', 'Model, Runtime & Dependency Configuration', 'Runtime supply chain', 'Model provider/name/version, inference parameters, fallback models, runtime framework, SDKs, packages, container image, and deployment runtime.'),
  createDimension('D06', 'Tools, Actions & Function Calls', 'Action surface', 'Tool list, function parameters, call permissions, read/write/delete capability, external side effects, user confirmation, and audit logs.'),
  createDimension('D07', 'Knowledge Base & RAG Pipeline', 'Retrieval pipeline', 'Knowledge sources, document ingestion, vector database, embeddings, retriever, reranker, permission filtering, citations, and RAG cleaning.'),
  createDimension('D08', 'External Systems, Connectors & Agent Protocols', 'Connector surface', 'Jira, Outlook, databases, CRM, MCP servers/tools, A2A, plugins, connectors, REST, GraphQL, WebSocket, and SSE.'),
  createDimension('D09', 'Data Assets, Secrets & Sensitive Information', 'Sensitive assets', 'User data, business data, PII, customer data, logs, tool results, tokens, API keys, secrets, credentials, and data classification.'),
  createDimension('D10', 'Data Flow, Storage & Trust Boundaries', 'Data movement', 'Data sources, processing nodes, storage, logs, cache, encryption, retention, cross-tenant/region flow, third-party sharing, and trust boundaries.'),
  createDimension('D11', 'Orchestration, Memory & State', 'State management', 'Agent workflow, planner, memory, short-term context, long-term memory, state store, context reset, session boundary, and human approval.'),
  createDimension('D12', 'Security Controls, Audit & Runtime Monitoring', 'Runtime controls', 'Input/output filtering, tool-call policy, permission validation, audit logs, runtime monitoring, anomaly alerts, red team, evals, and incident response.'),
]
const fallbackProviders: Record<string, ModelProvider> = {
  gemini: { label: 'Google Gemini', apiKeyLabel: 'Gemini API Key', models: [{ label: 'Gemini 3.5 Flash', value: 'gemini-3.5-flash' }], supported: 'Images and PDFs are native inputs; Office files are converted to text locally.' },
}

const hasVisibleGraph = computed(() => visibleNodes.value.length > 0)
const normalizedAssetGraph = computed<AgentAssetGraph | null>(() => {
  const graph = project.value?.functionReview?.agentAssetGraph || project.value?.assetGraph
  return graph ? normalizeAssetGraph(graph, project.value?.projectName) : null
})
const selectedAssetDetail = computed<AgentAssetNode | null>(() => {
  if (!selectedElement.value || selectedElement.value.kind !== 'node') return null
  return normalizedAssetGraph.value?.assets.find((asset) => asset.id === selectedElement.value?.id) || null
})
const selectedRelationshipDetail = computed<AgentAssetEdge | null>(() => {
  if (!selectedElement.value || selectedElement.value.kind !== 'edge') return null
  return normalizedAssetGraph.value?.relationships.find((edge) => edge.id === selectedElement.value?.id) || null
})
const assetCompleteness = computed(() => normalizedAssetGraph.value?.completeness)
const assetMissingCount = computed(() => {
  const unknownAssets = normalizedAssetGraph.value?.assets.filter((asset) => asset.status === 'unknown').length || 0
  const questions = assetCompleteness.value?.missing_questions.length || 0
  return unknownAssets + questions
})
const currentGraph = computed<FlowGraph>(() => ({
  nodes: visibleNodes.value as FlowGraph['nodes'],
  edges: visibleEdges.value as FlowGraph['edges'],
}))
const nodeSelectOptions = computed<Array<{ label: string; value: string }>>(() =>
  visibleNodes.value.map((node) => ({ label: String(node.data?.label || node.id), value: String(node.id) })),
)
const filteredRisks = computed(() => {
  const risks = project.value?.riskReview?.risks || []
  return riskFilter.value === 'all' ? risks : risks.filter((risk) => risk.severity === riskFilter.value)
})
const selectedRisk = computed(() => project.value?.riskReview?.risks.find((risk) => risk.id === highlightedRiskId.value) || null)
const activeRisks = computed(() => {
  if (!selectedElement.value || !project.value?.riskReview?.risks) return []
  return project.value.riskReview.risks.filter((risk) => {
    const location = selectedElement.value?.kind === 'node' ? risk.location?.nodes : risk.location?.edges
    return location?.some((id) => normalizeRiskLocationId(id) === selectedElement.value?.id)
  })
})
const featureRows = computed(() => project.value?.functionReview?.features || [])
const coverageRows = computed<DimensionCoverage[]>(() => {
  const current = project.value?.functionReview?.coverage_matrix || []
  const byId = new Map(current.map((item) => [item.dimension_id, item]))
  return assetDimensions.map((dimension) => normalizeDimension({ ...dimension, ...(byId.get(dimension.dimension_id) || {}) }))
})
const selectedDimension = computed(() => coverageRows.value.find((item) => item.dimension_id === selectedDimensionId.value) || coverageRows.value[0])
const missingQuestions = computed(() => project.value?.functionReview?.missing_questions || [])
const hasUnansweredMissingQuestions = computed(() => missingQuestions.value.some((item) => !missingAnswers[item.id]))
const hasGeneratedAssetGraph = computed(() => Boolean(normalizedAssetGraph.value?.assets.length && project.value?.functionReview?.agentAssetGraph))
const assetInventoryReady = computed(() => Boolean(project.value?.functionReview) && !isCurrentFunctionReviewing.value && hasGeneratedAssetGraph.value)
const canGenerateAssetGraph = computed(() => Boolean(project.value?.functionReview) && !hasGeneratedAssetGraph.value && !hasUnansweredMissingQuestions.value && !isCurrentFunctionReviewing.value)
const blockingMissingQuestions = computed(() => missingQuestions.value.filter((item) => item.priority === 'critical' && item.blocks_risk_mapping && !missingAnswers[item.id]))
const isRiskBlocked = computed(() => blockingMissingQuestions.value.length > 0)
const missingQuestionGroups = computed(() => {
  const groups = new Map<string, { dimension: DimensionCoverage; questions: any[] }>()
  missingQuestions.value.forEach((question) => {
    const dimension = coverageRows.value.find((item) => item.dimension_id === question.dimension_id) || assetDimensions[0]
    const group = groups.get(dimension.dimension_id) || { dimension, questions: [] }
    group.questions.push(question)
    groups.set(dimension.dimension_id, group)
  })
  return Array.from(groups.values())
})
const filteredMaterials = computed(() => (project.value?.materials || []).filter((file) => file.tag === uploadTag.value))
const providerCatalog = computed(() => Object.keys(modelProviders.value).length ? modelProviders.value : fallbackProviders)
const providerOptions = computed(() => Object.entries(providerCatalog.value).map(([value, item]) => ({ label: item.label, value })))
const selectedProviderInfo = computed(() => providerCatalog.value[setup.provider])
const modelOptions = computed(() => selectedProviderInfo.value?.models || [])
const isCurrentFunctionReviewing = computed(() => isBusyStatus(project.value?.status, 'function') || reviewing.value)
const isCurrentRiskReviewing = computed(() => isBusyStatus(project.value?.status, 'risk') || riskReviewing.value)
const isReviewThinking = computed(() => Boolean(project.value) && (isCurrentFunctionReviewing.value || isCurrentRiskReviewing.value))
const reviewThinkingTitle = computed(() => isCurrentRiskReviewing.value ? 'AI is mapping risk signals' : 'AI is reviewing assets')
const reviewThinkingDetail = computed(() => isCurrentRiskReviewing.value
  ? 'Tracing risky edges, trust boundaries, and control gaps across the graph.'
  : 'Reading materials, extracting agent components, and building the asset graph.')
const isGraphReviewing = computed(() => activeMap.value === 'risk' ? isCurrentRiskReviewing.value : isCurrentFunctionReviewing.value)
const hasRiskReview = computed(() => Boolean(project.value?.riskReview?.risks?.length))
const hasRenderableGraph = computed(() => hasVisibleGraph.value && !isGraphReviewing.value && (activeMap.value !== 'risk' || hasRiskReview.value))
const hasAssetGraph = computed(() => Boolean(
  normalizedAssetGraph.value?.assets?.length
  || project.value?.functionReview?.asset_graph_nodes?.length
  || project.value?.functionReview?.relationships?.length
  || project.value?.functionReview?.vueFlow?.nodes?.length
  || project.value?.functionMap?.nodes?.length,
))
const riskReadinessIssues = computed(() => {
  const issues: string[] = []
  if (!project.value?.functionReview) issues.push('Asset Review has not completed.')
  if (hasUnansweredMissingQuestions.value) issues.push('Supplemental information is still waiting for answers.')
  if (isRiskBlocked.value) issues.push('Critical supplemental information is unanswered.')
  if (!featureRows.value.length) issues.push('No capability has been identified.')
  if (!hasAssetGraph.value) issues.push('No asset graph nodes or relationships are available.')
  if (isCurrentRiskReviewing.value) issues.push('Risk map generation is already running.')
  return issues
})
const canGenerateRiskMap = computed(() => riskReadinessIssues.value.length === 0)
const manualEditorTitle = computed(() => manualInputCards.find((item) => item.key === manualEditorKey.value)?.label || 'Manual Input')
const manualEditorPlaceholder = computed(() => manualInputCards.find((item) => item.key === manualEditorKey.value)?.placeholder || '')
const materialPreviewTitle = computed(() => materialPreviewFile.value?.fileName || 'Material Preview')
const materialPreviewMeta = computed(() => {
  const file = materialPreviewFile.value
  if (!file) return ''
  return `${file.extension || file.contentType || 'file'} / ${formatBytes(file.size)} / ${formatTime(file.uploadedAt)}`
})
const materialVisualNote = computed(() => {
  const provider = project.value?.settings?.provider || setup.provider
  const label = asciiOnly(providerCatalog.value[String(provider)]?.label || String(provider || 'selected model')).replace(/\s*\/\s*$/, '')
  return `Image will be sent to ${label} as visual input.`
})
const assetReviewPhaseTitle = computed(() => {
  const status = String(project.value?.status || '').toLowerCase()
  if (status.includes('gap_check')) return 'Re-checking D01-D12 coverage'
  if (status.includes('assets')) return 'Building AI Agent Asset Inventory'
  if (status.includes('capabilities')) return 'Extracting Capability Inventory'
  if (status.includes('graph')) return 'Drawing the agent function flow'
  return 'Analyzing capabilities'
})
const assetReviewPhaseDetail = computed(() => {
  const status = String(project.value?.status || '').toLowerCase()
  if (status.includes('gap_check')) return 'Comparing answers and materials against the full D01-D12 asset model...'
  if (status.includes('assets')) return 'Reviewing identities, inputs, tools, data, trust boundaries, memory, and runtime controls...'
  if (status.includes('capabilities')) return 'Splitting the agent behavior into concrete executable capabilities...'
  if (status.includes('graph')) return 'Composing a detailed functional flow with assets, systems, storage, and agent decisions...'
  return 'Mapping signals, edges, and context into a structured graph...'
})
const manualEditorText = computed({
  get: () => manualInputs[manualEditorKey.value] || '',
  set: (value: string) => {
    manualInputs[manualEditorKey.value] = value
  },
})

watch(() => setup.provider, ensureValidModel)

watch([project, activeMap], () => {
  const graph = activeDisplayGraph()
  const nodes = decorateRiskNodes(normalizeNodes(graph?.nodes || []))
  const edges = normalizeEdges(graph?.edges || [])
  visibleEdges.value = edges
  visibleNodes.value = activeMap.value === 'risk' || Boolean(project.value?.functionReview?.features?.length)
    ? layoutRiskFlow(nodes)
    : graphNeedsLayout(nodes)
      ? layoutGraphNodes(nodes, edges)
      : nodes
  selectedElement.value = null
  highlightedRiskId.value = ''
}, { immediate: true })

async function loadProjects(quiet = false) {
  lastAction.value = loadProjects
  if (!quiet) error.value = ''
  try {
    projects.value = await agentSecurityReviewApi.listProjects()
    if (project.value) {
      const latest = projects.value.find((item) => item.projectId === project.value?.projectId)
      if (latest && latest.status !== project.value.status && isBusyStatus(project.value.status)) {
        await selectProject(project.value.projectId)
      }
      if (latest && isErrorStatus(latest.status) && latest.error) {
        error.value = cleanJobError(latest.error)
      }
    }
  } catch (err) {
    setError(err)
  }
}

async function loadModelProviders() {
  try {
    modelProviders.value = await agentSecurityReviewApi.listModelProviders()
    if (!modelProviders.value[setup.provider]) {
      setup.provider = Object.keys(modelProviders.value)[0] || 'gemini'
    }
    ensureValidModel()
  } catch (err) {
    setError(err)
  }
}

async function selectProject(projectId: string) {
  lastAction.value = () => selectProject(projectId)
  error.value = ''
  try {
    project.value = await agentSecurityReviewApi.getProject(projectId)
    if (isErrorStatus(project.value.status) && project.value.error) {
      error.value = cleanJobError(project.value.error)
    }
    setup.projectName = project.value.projectName
    setup.description = project.value.description
    setup.agentType = project.value.agentType
    setup.provider = String(project.value.settings?.provider || 'gemini')
    setup.modelName = String(project.value.settings?.modelName || 'gemini-3.5-flash')
    ensureValidModel()
    Object.assign(manualInputs, { ...defaultManualInputs, ...(project.value.manualInputs || {}) })
    Object.keys(missingAnswers).forEach((key) => delete missingAnswers[key])
    Object.keys(missingAnswerLocks).forEach((key) => delete missingAnswerLocks[key])
    Object.assign(missingAnswers, project.value.missingAnswers || {})
    Object.entries(project.value.missingAnswers || {}).forEach(([key, value]) => {
      if (value) missingAnswerLocks[key] = true
    })
    activeMap.value = project.value.riskReview ? 'risk' : 'function'
  } catch (err) {
    setError(err)
  }
}

async function createProject() {
  lastAction.value = createProject
  if (!setup.projectName.trim()) {
    message.warning('Project Name is required')
    return
  }
  try {
    const created = await agentSecurityReviewApi.createProject({
      ...setup,
      projectName: setup.projectName.trim(),
      model: selectedProviderInfo.value?.models.find((item) => item.value === setup.modelName)?.label || setup.modelName,
    })
    projectSetupOpen.value = false
    await loadProjects()
    await selectProject(created.projectId)
    message.success('Project created')
  } catch (err) {
    setError(err)
  }
}

async function saveProjectSetup() {
  if (!project.value) {
    await createProject()
    return
  }
  if (!setup.projectName.trim()) {
    message.warning('Project Name is required')
    return
  }
  try {
    project.value = await agentSecurityReviewApi.saveProjectContext(project.value.projectId, {
      projectName: setup.projectName.trim(),
      description: setup.description,
      agentType: setup.agentType,
      provider: setup.provider,
      modelName: setup.modelName,
      model: selectedProviderInfo.value?.models.find((item) => item.value === setup.modelName)?.label || setup.modelName,
    })
    projectSetupOpen.value = false
    await loadProjects()
    message.success('Project setup saved')
  } catch (err) {
    setError(err)
  }
}

function openProjectSetup(current?: ReviewProject) {
  error.value = ''
  setup.projectName = current?.projectName || ''
  setup.description = current?.description || ''
  setup.agentType = current?.agentType || 'RAG Agent'
  setup.provider = String(current?.settings?.provider || setup.provider || 'gemini')
  setup.modelName = String(current?.settings?.modelName || setup.modelName || 'gemini-3.5-flash')
  ensureValidModel()
  projectSetupOpen.value = true
}

function closeProject() {
  project.value = null
  activeMap.value = 'function'
  visibleNodes.value = []
  visibleEdges.value = []
  selectedElement.value = null
  void loadProjects()
}

async function deleteCurrentProject() {
  if (!project.value) return
  const projectId = project.value.projectId
  try {
    await agentSecurityReviewApi.deleteProject(projectId)
    closeProject()
    message.success('Project deleted')
  } catch (err) {
    setError(err)
  }
}

async function uploadFiles(files: File[]) {
  if (!project.value || !files.length) return
  lastAction.value = () => uploadFiles(files)
  try {
    await agentSecurityReviewApi.uploadMaterials(project.value.projectId, files, uploadTag.value)
    await selectProject(project.value.projectId)
    message.success('Materials uploaded')
  } catch (err) {
    setError(err)
  }
}

function openFilePicker() {
  fileInputRef.value?.click()
}

function handleFileInput(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  void uploadFiles(files)
  input.value = ''
}

function handleDrop(event: DragEvent) {
  dragging.value = false
  void uploadFiles(Array.from(event.dataTransfer?.files || []))
}

async function deleteMaterial(fileId: string) {
  if (!project.value) return
  try {
    await agentSecurityReviewApi.deleteMaterial(project.value.projectId, fileId)
    await selectProject(project.value.projectId)
  } catch (err) {
    setError(err)
  }
}

async function openMaterial(file: ReviewMaterial) {
  if (!project.value) return
  materialPreviewFile.value = file
  materialPreviewUrl.value = agentSecurityReviewApi.materialFileUrl(project.value.projectId, file.fileId)
  materialPreviewText.value = ''
  resetPreviewTransform()
  const extension = String(file.extension || '').toLowerCase()
  const contentType = String(file.contentType || '').toLowerCase()
  if (isImageMaterial(file)) {
    materialPreviewMode.value = 'image'
    materialPreviewOpen.value = true
    return
  }
  if (extension === '.pdf' || contentType.includes('pdf')) {
    materialPreviewMode.value = 'frame'
    materialPreviewOpen.value = true
    return
  }
  materialPreviewMode.value = 'text'
  materialPreviewOpen.value = true
  try {
    materialPreviewText.value = await agentSecurityReviewApi.previewMaterial(project.value.projectId, file.fileId)
  } catch (err) {
    materialPreviewMode.value = 'fallback'
    materialPreviewText.value = err instanceof Error ? err.message : 'Preview is not available for this file.'
  }
}

function openMaterialInNewTab() {
  if (!materialPreviewUrl.value) return
  window.open(materialPreviewUrl.value, '_blank', 'noopener,noreferrer')
}

function zoomPreview(delta: number) {
  previewZoom.value = Math.min(5, Math.max(0.25, Number((previewZoom.value + delta).toFixed(2))))
}

function resetPreviewTransform() {
  previewZoom.value = 1
  previewPan.x = 0
  previewPan.y = 0
}

function onPreviewWheel(event: WheelEvent) {
  zoomPreview(event.deltaY > 0 ? -0.1 : 0.1)
}

function startPreviewDrag(event: PointerEvent) {
  previewDrag.active = true
  previewDrag.startX = event.clientX
  previewDrag.startY = event.clientY
  previewDrag.panX = previewPan.x
  previewDrag.panY = previewPan.y
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function movePreviewDrag(event: PointerEvent) {
  if (!previewDrag.active) return
  previewPan.x = previewDrag.panX + event.clientX - previewDrag.startX
  previewPan.y = previewDrag.panY + event.clientY - previewDrag.startY
}

function endPreviewDrag(event: PointerEvent) {
  previewDrag.active = false
  const target = event.currentTarget as HTMLElement
  if (target.hasPointerCapture(event.pointerId)) target.releasePointerCapture(event.pointerId)
}

async function saveProviderKey() {
  try {
    await agentSecurityReviewApi.saveProviderApiKey(setup.provider, providerApiKey.value)
    message.success(`${selectedProviderInfo.value?.label || setup.provider} API Key saved`)
  } catch (err) {
    setError(err)
  }
}

async function testProviderConnection() {
  testingProvider.value = true
  try {
    if (providerApiKey.value) await agentSecurityReviewApi.saveProviderApiKey(setup.provider, providerApiKey.value)
    await agentSecurityReviewApi.testProvider(setup.provider, setup.modelName)
    message.success(`${selectedProviderInfo.value?.label || setup.provider} connection works`)
  } catch (err) {
    setError(err)
  } finally {
    testingProvider.value = false
  }
}

function ensureValidModel() {
  const models = providerCatalog.value[setup.provider]?.models || []
  if (models.length && !models.some((item) => item.value === setup.modelName)) {
    setup.modelName = models[0].value
  }
}

async function saveManualContext() {
  if (!project.value) return
  try {
    project.value = await agentSecurityReviewApi.saveProjectContext(project.value.projectId, { manualInputs, missingAnswers })
    message.success('Inputs saved')
  } catch (err) {
    setError(err)
  }
}

function lockMissingAnswers() {
  missingQuestions.value.forEach((item) => {
    missingAnswerLocks[item.id] = true
  })
}

function unlockMissingAnswer(id: string) {
  missingAnswerLocks[id] = false
}

function lockMissingAnswer(id: string) {
  if (missingAnswers[id]) missingAnswerLocks[id] = true
}

async function toggleMissingAnswerLock(id: string) {
  if (missingAnswerLocks[id]) {
    unlockMissingAnswer(id)
    return
  }
  lockMissingAnswer(id)
  if (!project.value) return
  try {
    project.value = await agentSecurityReviewApi.saveProjectContext(project.value.projectId, { manualInputs, missingAnswers })
  } catch (err) {
    setError(err)
  }
}

function cancelMissingAnswer(id: string) {
  missingAnswers[id] = 'None'
  missingAnswerLocks[id] = true
}

async function startFunctionReview() {
  if (!project.value) return
  lastAction.value = startFunctionReview
  reviewing.value = true
  try {
    project.value = await agentSecurityReviewApi.startFunctionReview(project.value.projectId, { manualInputs, missingAnswers })
    activeMap.value = 'function'
    startPolling()
    await loadProjects()
    message.success('Asset review started')
  } catch (err) {
    setError(err)
  } finally {
    reviewing.value = false
  }
}

async function saveFunctionMap() {
  if (!project.value) return
  try {
    await agentSecurityReviewApi.saveFunctionMap(project.value.projectId, currentGraph.value)
    project.value.functionMap = currentGraph.value
    message.success('Function map saved')
  } catch (err) {
    setError(err)
  }
}

async function updateFunctionMap(mode: 'direct' | 'review_again' = 'review_again') {
  if (!project.value) return
  lockMissingAnswers()
  reviewing.value = true
  try {
    project.value = await agentSecurityReviewApi.updateFunctionMap(project.value.projectId, { manualInputs, missingAnswers, functionMap: currentGraph.value, mode })
    activeMap.value = 'function'
    missingPanelCollapsed.value = true
    startPolling()
    await loadProjects()
    Object.keys(missingAnswerLocks).forEach((key) => delete missingAnswerLocks[key])
    Object.entries(project.value.missingAnswers || {}).forEach(([key, value]) => {
      if (value) missingAnswerLocks[key] = true
    })
    message.success(mode === 'direct' ? 'Progressive asset generation started' : 'Asset coverage review started')
  } catch (err) {
    setError(err)
  } finally {
    reviewing.value = false
  }
}

async function generateRiskMap() {
  if (!project.value) return
  if (isRiskBlocked.value) {
    message.warning('Risk Map is not ready. Please answer critical supplemental information first.')
    activeMap.value = 'function'
    return
  }
  lastAction.value = generateRiskMap
  riskReviewing.value = true
  try {
    const riskInputs = additionalRiskNotes.value.trim()
      ? { ...manualInputs, extraNotes: `${manualInputs.extraNotes || ''}\n\nAdditional risk focus:\n${additionalRiskNotes.value.trim()}`.trim() }
      : manualInputs
    project.value = await agentSecurityReviewApi.generateRiskMap(project.value.projectId, { manualInputs: riskInputs, missingAnswers, functionMap: project.value.functionMap || currentGraph.value })
    activeMap.value = 'risk'
    startPolling()
    await loadProjects()
    message.success('Risk review started')
  } catch (err) {
    setError(err)
  } finally {
    riskReviewing.value = false
  }
}

async function generateAssetGraph() {
  if (!project.value) return
  if (hasUnansweredMissingQuestions.value) {
    message.warning('Please answer all supplemental questions first')
    return
  }
  lockMissingAnswers()
  await updateFunctionMap('direct')
}

async function cancelCurrentReview() {
  if (!project.value) return
  try {
    project.value = await agentSecurityReviewApi.cancelReview(project.value.projectId)
    reviewing.value = false
    riskReviewing.value = false
    stopPolling()
    await loadProjects(true)
    message.info('AI review cancelled')
  } catch (err) {
    setError(err)
  }
}

function onNodeClick(event: { node: any }) {
  selectedElement.value = { kind: 'node', id: event.node.id }
  if (activeMap.value === 'risk') {
    highlightedRiskId.value = ''
    highlightRiskLocations([], [], event.node.id)
    return
  }
  detailDraft.label = String(event.node.data?.label || '')
  detailDraft.nodeType = String(event.node.data?.nodeType || '')
  detailDraft.description = String(event.node.data?.description || '')
}

function onEdgeClick(event: { edge: any }) {
  selectedElement.value = { kind: 'edge', id: event.edge.id }
  if (activeMap.value === 'risk') {
    highlightedRiskId.value = ''
    highlightRiskLocations([], [], undefined, event.edge.id)
    return
  }
  detailDraft.label = String(event.edge.label || '')
  detailDraft.flowType = String(event.edge.data?.flowType || '')
  detailDraft.description = String(event.edge.data?.description || '')
}

function applyDetailEdit() {
  if (!selectedElement.value) return
  if (selectedElement.value.kind === 'node') {
    visibleNodes.value = visibleNodes.value.map((node) => node.id === selectedElement.value?.id ? { ...node, data: { ...node.data, label: detailDraft.label, nodeType: detailDraft.nodeType, description: detailDraft.description } } : node)
  } else {
    visibleEdges.value = visibleEdges.value.map((edge) => edge.id === selectedElement.value?.id ? { ...edge, label: detailDraft.label, data: { ...edge.data, flowType: detailDraft.flowType, description: detailDraft.description } } : edge)
  }
  markMapEdited()
}

function deleteSelected() {
  if (!selectedElement.value) return
  if (selectedElement.value.kind === 'node') {
    visibleNodes.value = visibleNodes.value.filter((node) => node.id !== selectedElement.value?.id)
    visibleEdges.value = visibleEdges.value.filter((edge) => edge.source !== selectedElement.value?.id && edge.target !== selectedElement.value?.id)
  } else {
    visibleEdges.value = visibleEdges.value.filter((edge) => edge.id !== selectedElement.value?.id)
  }
  selectedElement.value = null
  markMapEdited()
}

function openNodeEditor() {
  nodeDraft.label = ''
  nodeDraft.nodeType = 'Agent Runtime'
  nodeDraft.description = ''
  nodeEditorOpen.value = true
}

function openEdgeEditor() {
  edgeDraft.source = visibleNodes.value[0]?.id || ''
  edgeDraft.target = visibleNodes.value[1]?.id || ''
  edgeDraft.label = ''
  edgeDraft.flowType = 'Data Flow'
  edgeDraft.description = ''
  edgeEditorOpen.value = true
}

function saveNodeDraft() {
  const id = slugify(nodeDraft.label || `node-${Date.now()}`)
  visibleNodes.value.push({ id, type: 'custom', position: { x: 120 + visibleNodes.value.length * 40, y: 120 + visibleNodes.value.length * 40 }, data: { ...nodeDraft } })
  nodeEditorOpen.value = false
  markMapEdited()
}

function saveEdgeDraft() {
  if (!edgeDraft.source || !edgeDraft.target) return
  visibleEdges.value.push({ id: `edge-${edgeDraft.source}-${edgeDraft.target}-${Date.now()}`, source: edgeDraft.source, target: edgeDraft.target, label: edgeDraft.label, data: { flowType: edgeDraft.flowType, description: edgeDraft.description } })
  edgeEditorOpen.value = false
  markMapEdited()
}

function activeDisplayGraph() {
  if (!project.value) return undefined
  if (activeMap.value === 'risk') return project.value.riskReview?.risks?.length ? buildReviewFlowGraph() : { nodes: [], edges: [] }
  if (normalizedAssetGraph.value?.assets.length) {
    return assetGraphToVueFlow(normalizedAssetGraph.value, {})
  }
  return project.value.functionReview?.features?.length ? buildReviewFlowGraph() : project.value.functionMap
}

function autoLayout() {
  if (activeMap.value === 'function' && normalizedAssetGraph.value?.assets.length) {
    visibleNodes.value = assetGraphToVueFlow(normalizedAssetGraph.value, {}, true).nodes
  } else {
    visibleNodes.value = layoutGraphNodes(visibleNodes.value, visibleEdges.value)
  }
  markMapEdited()
}

function layoutGraphNodes(nodes: any[], edges: any[]) {
  const layers = new Map<string, number>([
    ['user', 0],
    ['actor', 0],
    ['input', 1],
    ['frontend', 1],
    ['file-upload', 1],
    ['prompt', 1],
    ['asset', 2],
    ['identity', 2],
    ['uploaded-material', 2],
    ['uploaded-file', 2],
    ['system-prompt', 2],
    ['tool-spec', 2],
    ['rag-source', 2],
    ['api-endpoint', 2],
    ['feature', 2],
    ['backend', 3],
    ['agent-runtime', 3],
    ['llm', 4],
    ['rag-retriever', 4],
    ['vector-db', 4],
    ['file-parser', 4],
    ['tool-router', 4],
    ['tool', 5],
    ['external-api', 6],
    ['database', 6],
    ['file-storage', 6],
    ['authentication', 6],
    ['audit-log', 6],
    ['human-review', 6],
    ['output', 7],
  ])
  const buckets = new Map<number, any[]>()
  nodes.forEach((node) => {
    const type = normalizeType(node.data?.nodeType)
    const layer = layers.get(type) ?? inferLayerFromEdges(node.id, edges)
    buckets.set(layer, [...(buckets.get(layer) || []), node])
  })
  const layerWidth = activeMap.value === 'risk' ? 360 : 320
  const rowHeight = activeMap.value === 'risk' ? 210 : 190
  return nodes.map((node) => {
    const type = normalizeType(node.data?.nodeType)
    const layer = layers.get(type) ?? inferLayerFromEdges(node.id, edges)
    const bucket = buckets.get(layer) || []
    const index = bucket.findIndex((item) => item.id === node.id)
    const total = bucket.length
    const y = 90 + index * rowHeight + Math.max(0, 3 - total) * 48
    return {
      ...node,
      position: { x: 80 + layer * layerWidth, y },
    }
  })
}

function layoutRiskFlow(nodes: any[]) {
  const enriched = enrichRiskNodes(nodes)
  const buckets = new Map<number, any[]>()
  enriched.forEach((node) => {
    const stage = flowStage(node)
    buckets.set(stage, [...(buckets.get(stage) || []), node])
  })
  return enriched.map((node) => {
    const stage = flowStage(node)
    const bucket = buckets.get(stage) || []
    const index = bucket.findIndex((item) => item.id === node.id)
    const total = bucket.length
    const centerOffset = Math.max(0, 2 - total) * 70
    const userOffset = node.id === 'user' ? 250 : 0
    return {
      ...node,
      position: {
        x: 70 + stage * 310,
        y: 90 + index * 190 + centerOffset + userOffset,
      },
    }
  })
}

function flowStage(node: any) {
  if (node.id === 'user') return 0
  const text = `${node.data?.featureId || ''} ${node.data?.label || ''} ${node.data?.nodeType || ''} ${node.data?.description || ''}`.toLowerCase()
  if (text.includes('user') || text.includes('prompt') || text.includes('session')) return 1
  if (text.includes('ingest') || text.includes('batch') || text.includes('file') || text.includes('document') || text.includes('parser')) return 1
  if (text.includes('vector') || text.includes('rag') || text.includes('retriev') || text.includes('knowledge') || text.includes('embedding')) return 2
  if (text.includes('agent') || text.includes('runtime') || text.includes('query') || text.includes('execution') || text.includes('orchestrat')) return 3
  if (text.includes('external') || text.includes('tool') || text.includes('api') || text.includes('jira') || text.includes('outlook')) return 4
  return 2
}

function buildReviewFlowGraph() {
  const features = project.value?.functionReview?.features || []
  if (!features.length) return project.value?.riskReview?.vueFlow || project.value?.functionMap
  const assetNodes = buildAssetGraphNodes()
  const nodes = [
    {
      id: 'user',
      type: 'custom',
      position: { x: 0, y: 0 },
      data: { label: 'User Request', nodeType: 'User', description: 'User input or uploaded context entering the workflow.' },
    },
    ...features.map((feature) => ({
      id: feature.id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: {
        label: feature.name,
        nodeType: inferFeatureNodeType(feature),
        description: feature.description,
        featureId: feature.id,
      },
    })),
    ...assetNodes,
  ]
  const edges = [...buildFeatureFlowEdges(features), ...buildAssetGraphEdges(features, assetNodes)]
  return { nodes, edges }
}

function buildAssetGraphNodes() {
  const review = project.value?.functionReview
  const nodes: any[] = []
  const seen = new Set<string>()
  const addNode = (node: any) => {
    const id = String(node.id || node.asset_id || '')
    if (!id || seen.has(id)) return
    seen.add(id)
    nodes.push({
      id,
      type: 'custom',
      position: { x: 0, y: 0 },
      data: {
        label: String(node.label || node.name || id),
        nodeType: String(node.type || node.asset_type || 'Asset'),
        description: String(node.description || node.dimension_id || ''),
        assetId: String(node.asset_id || id),
      },
    })
  }
  ;(review?.asset_graph_nodes || []).forEach(addNode)
  coverageRows.value.forEach((dimension) => {
    dimension.detected_assets.forEach((asset) => addNode({
      id: asset.asset_id,
      label: asset.name,
      type: asset.asset_type,
      description: `${dimension.dimension_id} ${dimension.dimension_name}: ${asset.description || asset.risk_level}`,
      asset_id: asset.asset_id,
    }))
  })
  return nodes.slice(0, 36)
}

function buildAssetGraphEdges(features: any[], assetNodes: any[]) {
  const review = project.value?.functionReview
  const edges: any[] = []
  const nodeIds = new Set(['user', ...features.map((feature) => feature.id), ...assetNodes.map((node) => node.id)])
  const addEdge = (id: string, source: string, target: string, label: string) => {
    if (!source || !target || source === target || !nodeIds.has(source) || !nodeIds.has(target)) return
    if (edges.some((edge) => edge.source === source && edge.target === target && edge.label === label)) return
    edges.push({ id, source, target, label, type: 'smoothstep', data: { flowType: label } })
  }
  ;(review?.asset_graph_edges || []).forEach((edge: any) => addEdge(String(edge.id || `asset-edge-${edge.source}-${edge.target}`), String(edge.source || ''), String(edge.target || ''), String(edge.label || edge.type || 'Asset link')))
  ;(review?.relationships || []).forEach((edge: any) => addEdge(String(edge.id || `rel-${edge.source}-${edge.target}`), String(edge.source || ''), String(edge.target || ''), String(edge.label || edge.type || 'Relationship')))
  features.forEach((feature) => {
    ;(feature.related_asset_ids || []).forEach((assetId: string) => addEdge(`asset-${assetId}-${feature.id}`, assetId, feature.id, 'Supports capability'))
  })
  return edges
}

function buildFeatureFlowEdges(features: any[]) {
  const edges: any[] = []
  const featureIds = new Set(features.map((feature) => feature.id))
  const addEdge = (id: string, source: string, target: string, label: string, type: 'straight' | 'smoothstep' | 'bezier') => {
    if (!source || !target || source === target) return
    if (edges.some((edge) => edge.source === source && edge.target === target && edge.label === label)) return
    edges.push({ id, source, target, label, type, data: { flowType: label } })
  }
  features.forEach((feature) => {
    const trigger = String(feature.trigger || '').toLowerCase()
    if (trigger.includes('user') || trigger.includes('chat') || trigger.includes('prompt') || trigger.includes('manual')) {
      addEdge(`flow-user-${feature.id}`, 'user', feature.id, 'User input', 'bezier')
    }
    ;(feature.flow_next || []).forEach((target: string) => {
      if (featureIds.has(target)) addEdge(`flow-${feature.id}-${target}`, feature.id, target, 'Next step', flowStageForEdge(feature, features.find((item) => item.id === target)))
    })
  })
  const retrievalFeatures = features.filter((feature) => inferFeatureNodeType(feature) === 'Vector Store')
  const agentFeatures = features.filter((feature) => inferFeatureNodeType(feature) === 'Agent Runtime')
  retrievalFeatures.forEach((retrieval) => {
    agentFeatures.forEach((agent) => addEdge(`flow-${retrieval.id}-${agent.id}-rag`, retrieval.id, agent.id, 'RAG context', 'straight'))
  })
  if (!edges.length) {
    features.slice(0, -1).forEach((feature, index) => addEdge(`flow-seq-${feature.id}-${features[index + 1].id}`, feature.id, features[index + 1].id, 'Next step', 'smoothstep'))
  }
  return edges
}

function flowStageForEdge(source: any, target: any) {
  const sourceStage = flowStage({ id: source.id, data: { label: source.name, nodeType: inferFeatureNodeType(source), description: source.description } })
  const targetStage = flowStage({ id: target.id, data: { label: target.name, nodeType: inferFeatureNodeType(target), description: target.description } })
  if (Math.abs(sourceStage - targetStage) > 1) return 'bezier'
  if (sourceStage === targetStage) return 'smoothstep'
  return 'straight'
}

function inferFeatureNodeType(feature: any) {
  const text = `${feature.name || ''} ${feature.description || ''} ${feature.trigger || ''} ${(feature.components || []).join(' ')} ${(feature.inputs || []).join(' ')} ${(feature.outputs || []).join(' ')}`.toLowerCase()
  if (text.includes('vector') || text.includes('embedding') || text.includes('rag') || text.includes('retriev') || text.includes('knowledge')) return 'Vector Store'
  if (text.includes('agent') || text.includes('runtime') || text.includes('query') || text.includes('orchestrat') || text.includes('llm')) return 'Agent Runtime'
  if (text.includes('file') || text.includes('document') || text.includes('parser') || text.includes('ingest') || text.includes('batch')) return 'Ingestion Pipeline'
  if (text.includes('external') || text.includes('api') || text.includes('jira') || text.includes('outlook') || (feature.tools || []).length) return 'External System'
  return 'Feature'
}

function enrichRiskNodes(nodes: any[]) {
  return nodes.map((node) => {
    const feature = featureForRiskNode(node)
    return {
      ...node,
      data: {
        ...node.data,
        label: feature?.name || node.data?.label || node.label || node.id,
        nodeType: feature ? inferFeatureNodeType(feature) : (node.data?.nodeType || displayRiskNodeType(node.type || node.data?.nodeType)),
        description: feature?.description || node.data?.description || '',
        featureId: feature?.id || extractFeatureId(node.label || node.id),
      },
    }
  })
}

function featureForRiskNode(node: any) {
  const featureId = extractFeatureId(node.id || node.label || node.data?.label)
  const features = project.value?.functionReview?.features || []
  if (featureId) return features.find((feature) => feature.id === featureId)
  const nodeId = String(node.id || '').toLowerCase()
  const lookup: Record<string, string> = {
    realtime_ingestion: 'F001',
    batch_processing: 'F002',
    vector_indexing: 'F003',
    agent_query: 'F004',
    external_integration: 'F005',
  }
  return features.find((feature) => feature.id === lookup[nodeId])
}

function extractFeatureId(value: unknown) {
  return String(value || '').match(/F\d{3}/)?.[0]
}

function displayRiskNodeType(value: unknown) {
  const normalized = String(value || '').toLowerCase()
  if (normalized.includes('input')) return 'User'
  if (normalized.includes('pipeline')) return 'Ingestion Pipeline'
  if (normalized.includes('storage')) return 'Vector Store'
  if (normalized.includes('runtime')) return 'Agent Runtime'
  if (normalized.includes('tool')) return 'External System'
  return value || 'Feature'
}

function graphNeedsLayout(nodes: any[]) {
  if (nodes.length < 2) return false
  return nodes.some((node, index) => nodes.slice(index + 1).some((other) => {
    const dx = Math.abs(Number(node.position?.x || 0) - Number(other.position?.x || 0))
    const dy = Math.abs(Number(node.position?.y || 0) - Number(other.position?.y || 0))
    return dx < 210 && dy < 130
  }))
}

function inferLayerFromEdges(nodeId: string, edges = visibleEdges.value) {
  const incoming = edges.filter((edge) => edge.target === nodeId).length
  const outgoing = edges.filter((edge) => edge.source === nodeId).length
  if (!incoming) return 1
  if (!outgoing) return 7
  return 3
}

function highlightRisk(riskId: string) {
  highlightedRiskId.value = riskId
  const risk = project.value?.riskReview?.risks.find((item) => item.id === riskId)
  if (!risk) return
  selectedElement.value = null
  highlightRiskLocations((risk.location.nodes || []).map(normalizeRiskLocationId), risk.location.edges || [])
}

function normalizeRiskLocationId(id: unknown) {
  const raw = String(id || '')
  const featureId = extractFeatureId(raw)
  if (featureId) return featureId
  const legacy: Record<string, string> = {
    realtime_ingestion: 'F001',
    batch_processing: 'F002',
    vector_indexing: 'F003',
    agent_query: 'F004',
    external_integration: 'F005',
  }
  return legacy[raw] || raw
}

function highlightRiskLocations(nodeIds: string[], edgeIds: string[], selectedNodeId?: string, selectedEdgeId?: string) {
  visibleNodes.value = visibleNodes.value.map((node) => ({
    ...node,
    class: nodeIds.includes(node.id) || node.id === selectedNodeId ? 'highlighted' : '',
  }))
  visibleEdges.value = visibleEdges.value.map((edge) => ({
    ...edge,
    animated: edgeIds.includes(edge.id) || edge.id === selectedEdgeId,
    class: edgeIds.includes(edge.id) || edge.id === selectedEdgeId ? 'highlighted' : '',
  }))
}

function markMapEdited() {
  if (project.value && activeMap.value === 'function') project.value.status = 'function_map_ready'
}

function normalizeNodes(nodes: FlowGraph['nodes']) {
  return nodes.map((node, index) => ({
    ...node,
    type: node.type === 'asset' || node.type === 'layerGroup' ? node.type : 'custom',
    targetPosition: Position.Left,
    sourcePosition: Position.Right,
    position: node.position || { x: 80 + index * 120, y: 120 },
    data: {
      ...node.data,
      label: node.data?.label || (node as any).label || node.id,
      nodeType: inferNodeType(node.data?.nodeType || (node as any).type, node.data?.label || (node as any).label || node.id, node.data?.description || ''),
      description: node.data?.description || '',
    },
  }))
}

function normalizeEdges(edges: Array<FlowGraph['edges'][number] & Record<string, any>>) {
  return edges.map((edge) => ({
    ...edge,
    label: edge.label || edge.data?.flowType || 'Flow',
    type: edge.type || inferEdgeType(edge),
    animated: Boolean(edge.animated),
    markerEnd: edge.markerEnd || {
      type: MarkerType.ArrowClosed,
      color: edgeColor(edge.data?.flowType || edge.label),
      width: 18,
      height: 18,
    },
    interactionWidth: 18,
    data: { ...(edge.data || {}) },
    style: { stroke: edgeColor(edge.data?.flowType || edge.label), strokeWidth: 2.4, ...(edge.style || {}) },
    labelStyle: { fill: '#334155', fontSize: 11, fontWeight: 800, ...(edge.labelStyle || {}) },
    labelBgStyle: { fill: 'rgba(255, 255, 255, 0.94)', fillOpacity: 0.94, stroke: 'rgba(203, 213, 225, 0.9)', strokeWidth: 1, ...(edge.labelBgStyle || {}) },
    labelBgPadding: [6, 4],
    labelBgBorderRadius: 6,
  }))
}

function inferEdgeType(edge: Record<string, any>) {
  const label = String(edge.label || edge.data?.flowType || '').toLowerCase()
  if (label.includes('prompt') || label.includes('retrieval') || label.includes('return')) return 'bezier'
  if (label.includes('tool') || label.includes('rag context') || label.includes('response')) return 'straight'
  return 'smoothstep'
}

function decorateRiskNodes(nodes: any[]) {
  const risks = project.value?.riskReview?.risks || []
  if (activeMap.value !== 'risk' || !risks.length) return nodes
  const severityRank: Record<string, number> = { low: 1, medium: 2, high: 3, critical: 4 }
  return nodes.map((node) => {
    const nodeRisks = risks.filter((risk) => risk.location?.nodes?.includes(node.id))
    if (!nodeRisks.length) return node
    const top = nodeRisks.reduce((best, risk) => severityRank[risk.severity] > severityRank[best.severity] ? risk : best, nodeRisks[0])
    return { ...node, data: { ...node.data, riskSeverity: top.severity, risks: nodeRisks } }
  })
}

function inferNodeType(type: unknown, label: unknown, description: unknown) {
  const rawType = String(type || '').toLowerCase()
  const text = `${rawType} ${String(label || '')} ${String(description || '')}`.toLowerCase()
  if (rawType && !['component', 'custom', 'node'].includes(rawType)) return type
  if (text.includes('user') || text.includes('chat ui')) return 'User'
  if (text.includes('input') || text.includes('upload') || text.includes('prompt')) return 'Input'
  if (text.match(/\bf\d{2,}/) || text.includes('capability') || text.includes('feature')) return 'Feature'
  if (text.includes('agent runtime') || text.includes('runtime')) return 'Agent Runtime'
  if (text.includes('llm') || text.includes('gemini') || text.includes('model')) return 'LLM'
  if (text.includes('rag') || text.includes('retriever')) return 'RAG Retriever'
  if (text.includes('vector')) return 'Vector DB'
  if (text.includes('parser') || text.includes('image processing') || text.includes('file')) return 'File Parser'
  if (text.includes('tool router')) return 'Tool Router'
  if (text.includes('tool') || text.includes('connector')) return 'Tool'
  if (text.includes('api') || text.includes('external')) return 'External API'
  if (text.includes('database') || text.includes('db')) return 'Database'
  if (text.includes('auth') || text.includes('permission')) return 'Authentication'
  if (text.includes('audit') || text.includes('log')) return 'Audit Log'
  if (text.includes('human') || text.includes('approval')) return 'Human Review'
  if (text.includes('output') || text.includes('response') || text.includes('result')) return 'Output'
  return 'Feature'
}

function nodeIcon(type: unknown) {
  const value = String(type || '').toLowerCase()
  if (value.includes('user')) return 'U'
  if (value.includes('input')) return 'I'
  if (value.includes('feature')) return 'F'
  if (value.includes('output')) return 'O'
  if (value.includes('tool')) return 'T'
  if (value.includes('rag') || value.includes('vector')) return 'R'
  if (value.includes('llm')) return 'L'
  if (value.includes('file')) return 'P'
  if (value.includes('api')) return 'A'
  if (value.includes('database')) return 'D'
  if (value.includes('auth')) return 'A'
  return 'C'
}

function displayNodeType(type: unknown) {
  return String(type || 'Feature')
}

function edgeColor(type: unknown) {
  const value = String(type || '').toLowerCase()
  if (value.includes('tool')) return '#16a34a'
  if (value.includes('rag') || value.includes('retrieval')) return '#d97706'
  if (value.includes('api')) return '#dc2626'
  if (value.includes('file')) return '#0284c7'
  if (value.includes('prompt')) return '#7c3aed'
  if (value.includes('database')) return '#475569'
  return '#94a3b8'
}

function normalizeType(type: unknown) {
  return String(type || 'component').toLowerCase().replace(/[^a-z0-9]+/g, '-')
}

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || `node_${Date.now()}`
}

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString() : ''
}

function projectInitial(value: string) {
  return (value || 'A').trim().slice(0, 1).toUpperCase()
}

function isBusyStatus(status?: string, mode?: 'function' | 'risk') {
  const value = String(status || '').toLowerCase()
  const functionBusy = value === 'asset_review_running'
    || value === 'asset_review_gap_check_running'
    || value === 'asset_review_assets_running'
    || value === 'asset_review_capabilities_running'
    || value === 'asset_review_graph_running'
    || value.includes('reviewing functions')
  if (mode === 'function') return functionBusy
  if (mode === 'risk') return value.includes('risk_reviewing') || value.includes('risk reviewing')
  return functionBusy || value.includes('risk_reviewing') || value.includes('risk reviewing')
}

function isErrorStatus(status?: string) {
  return String(status || '').toLowerCase() === 'error'
}

function isProjectBusy(item: ReviewProject) {
  return isBusyStatus(item.status)
}

function projectStatusLabel(status?: string) {
  const value = String(status || '').toLowerCase()
  if (value === 'review_cancelled') return 'Review Cancelled'
  if (value.includes('gap_check')) return 'Checking Coverage'
  if (value.includes('assets')) return 'Generating Asset Inventory'
  if (value.includes('capabilities')) return 'Generating Capabilities'
  if (value.includes('graph')) return 'Generating Function Flow'
  if (isBusyStatus(status, 'function')) return 'Reviewing assets'
  if (isBusyStatus(status, 'risk')) return 'Generating risks'
  if (isErrorStatus(status)) return 'Failed'
  const labels: Record<string, string> = {
    draft: 'Draft',
    materials_uploaded: 'Materials Uploaded',
    asset_review_completed: 'Asset Review Completed',
    missing_info_required: 'Missing Info Required',
    missing_info_answered: 'Missing Info Answered',
    function_map_ready: 'Function Map Ready',
    risk_map_ready: 'Risk Map Ready',
  }
  if (labels[value]) return labels[value]
  if (!status) return 'Draft'
  return status.replace(/([a-z])([A-Z])/g, '$1 $2')
}

function projectCardDescription(item: ReviewProject) {
  if (isProjectBusy(item)) return 'AI review is running in the background. You can leave this page and come back later.'
  if (item.functionReview && !item.riskReview) return 'Asset review and function map are ready. Complete blockers before risk mapping.'
  if (item.riskReview) return 'Risk overlay and report are available for review.'
  return item.description || 'Prepare materials and run the first asset review.'
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    await loadProjects(true)
    if (project.value && isBusyStatus(project.value.status)) {
      try {
        const latest = await agentSecurityReviewApi.getProject(project.value.projectId)
        const wasBusy = isBusyStatus(project.value.status)
        project.value = latest
        if (isErrorStatus(latest.status)) {
          error.value = cleanJobError(latest.error || 'Background review failed.')
          message.error(error.value)
        }
        if (wasBusy && !isBusyStatus(latest.status) && latest.functionReview && activeMap.value === 'function') {
          await nextTick()
          autoLayout()
          await saveFunctionMap()
        }
      } catch (err) {
        setError(err)
      }
    }
    const stillBusy = projects.value.some((item) => isBusyStatus(item.status)) || Boolean(project.value && isBusyStatus(project.value.status))
    if (!stillBusy && pollTimer) {
      window.clearInterval(pollTimer)
      pollTimer = undefined
    }
  }, 3000)
}

function isImageMaterial(file: { extension?: string; contentType?: string }) {
  return ['.png', '.jpg', '.jpeg', '.webp'].includes(String(file.extension || '').toLowerCase())
    || String(file.contentType || '').startsWith('image/')
}

function openManualEditor(key: keyof ManualInputs) {
  manualEditorKey.value = key
  manualEditorOpen.value = true
}

function manualInputStatus(key: keyof ManualInputs) {
  const value = manualInputs[key] || ''
  if (!value.trim()) return 'Empty'
  return `${value.trim().length} chars`
}

function manualPreview(value: string, fallback: string) {
  const text = (value || '').replace(/\s+/g, ' ').trim()
  if (!text) return fallback
  return text.length > 118 ? `${text.slice(0, 118)}...` : text
}

async function saveManualFromModal() {
  await saveManualContext()
  manualEditorOpen.value = false
}

function openFeatureDetail(feature: any) {
  selectedFeature.value = feature
  featureDetailOpen.value = true
}

function createDimension(dimension_id: string, dimension_name: string, dimension_zh_name: string, summary: string): DimensionCoverage {
  return {
    dimension_id,
    dimension_name,
    dimension_zh_name,
    status: 'unknown',
    coverage_score: 0,
    confidence: 0,
    summary,
    detected_assets: [],
    detected_items: [],
    missing_fields: [],
    evidence: [],
    related_capability_ids: [],
    related_graph_node_ids: [],
    unanswered_question_count: 0,
    potential_risk_hints: [],
  }
}

function normalizeDimension(dimension: DimensionCoverage): DimensionCoverage {
  const statusAliases: Record<string, DimensionCoverage['status']> = {
    missing_info: 'partial',
    not_found: 'missing',
  }
  const base = assetDimensions.find((item) => item.dimension_id === dimension.dimension_id)
  const status = statusAliases[String(dimension.status)] || dimension.status || 'unknown'
  const detectedAssets = normalizeDetectedAssets((dimension.detected_assets?.length ? dimension.detected_assets : dimension.detected_items) || [], dimension.dimension_id)
  return {
    ...dimension,
    dimension_name: base?.dimension_name || dimension.dimension_name,
    dimension_zh_name: base?.dimension_zh_name || dimension.dimension_name,
    status,
    coverage_score: Number(dimension.coverage_score ?? dimension.confidence ?? 0),
    confidence: Number(dimension.confidence || 0),
    detected_assets: detectedAssets,
    detected_items: detectedAssets.map((item) => item.name),
    evidence: normalizeEvidenceItems(dimension.evidence || []),
    related_graph_node_ids: dimension.related_graph_node_ids || dimension.related_capability_ids || [],
    potential_risk_hints: dimension.potential_risk_hints || [],
  }
}

function normalizeDetectedAssets(value: unknown[], dimensionId: string) {
  return value.map((item, index) => {
    if (typeof item === 'string') {
      return { asset_id: `asset_${dimensionId}_${index + 1}`, asset_type: 'asset', name: item, description: item, properties: {}, source_dimension_id: dimensionId, confidence: 0, risk_level: 'unknown' as const }
    }
    const asset = item as Record<string, any>
    return {
      asset_id: String(asset.asset_id || `asset_${dimensionId}_${index + 1}`),
      asset_type: String(asset.asset_type || 'asset'),
      name: String(asset.name || asset.asset_id || `Asset ${index + 1}`),
      description: String(asset.description || ''),
      properties: asset.properties || {},
      source_dimension_id: String(asset.source_dimension_id || dimensionId),
      confidence: Number(asset.confidence || 0),
      risk_level: asset.risk_level || 'unknown',
    }
  })
}

function normalizeEvidenceItems(value: unknown[]) {
  return value.map((item, index) => {
    if (typeof item === 'string') {
      return { evidence_id: `ev_${index + 1}`, source_type: 'inferred' as const, source_name: 'Evidence', excerpt: item, confidence: 0 }
    }
    const evidence = item as Record<string, any>
    return {
      evidence_id: String(evidence.evidence_id || `ev_${index + 1}`),
      source_type: evidence.source_type || 'inferred',
      source_name: String(evidence.source_name || ''),
      excerpt: String(evidence.excerpt || ''),
      confidence: Number(evidence.confidence || 0),
    }
  })
}

function selectDimension(dimensionId: string) {
  selectedDimensionId.value = dimensionId
  selectedElement.value = null
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = undefined
  }
}

function openDimensionDetail(dimensionId: string) {
  selectDimension(dimensionId)
  dimensionDetailOpen.value = true
}

function dimensionHasAssets(dimension: DimensionCoverage) {
  return Boolean(dimension.detected_assets?.length)
}

function dimensionAssetStatusLabel(dimension: DimensionCoverage) {
  return dimensionHasAssets(dimension) ? 'Present' : 'Not found'
}

function dimensionAssetNames(dimension: DimensionCoverage) {
  return dimension.detected_assets.map((asset) => asset.name || asset.asset_id).slice(0, 4)
}

function asciiOnly(value: unknown) {
  return String(value || '').replace(/[^\x20-\x7E]+/g, '').replace(/\s+/g, ' ').trim()
}

function formatConfidence(value: unknown) {
  const number = Number(value || 0)
  if (!number) return '0%'
  return `${Math.round(number <= 1 ? number * 100 : number)}%`
}

function formatMappedDimensions(value: unknown) {
  if (!Array.isArray(value) || !value.length) return '-'
  return value.join(', ')
}

function formatEvidenceItems(value: unknown) {
  if (!Array.isArray(value) || !value.length) return '-'
  return value.map((item: any) => `${item.source_name || item.source_type || 'Evidence'}: ${item.excerpt || ''}`).join('\n')
}

function relatedQuestions(dimensionId: string) {
  return missingQuestions.value.filter((item) => item.dimension_id === dimensionId)
}

function missingPriorityType(priority: string) {
  if (priority === 'critical' || priority === 'high') return 'error'
  if (priority === 'medium') return 'warning'
  return 'info'
}

function formatList(value: unknown) {
  return Array.isArray(value) && value.length ? value.join(', ') : '-'
}

function formatStructured(value: unknown) {
  if (!value) return '-'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function setError(err: unknown) {
  const raw = err instanceof Error ? err.message : 'Request failed'
  error.value = cleanJobError(raw.replace(/Gemini 3 Pro via model id\s+/g, 'Gemini model id '))
  message.error(error.value)
}

function cleanJobError(value: string) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  const jsonStart = raw.indexOf('{')
  if (jsonStart >= 0) {
    try {
      const parsed = JSON.parse(raw.slice(jsonStart))
      const messageText = parsed?.error?.message || parsed?.message
      const statusText = parsed?.error?.status || parsed?.status
      if (messageText) return statusText ? `${statusText}: ${messageText}` : messageText
    } catch {
      // Fall through to readable raw text.
    }
  }
  return raw.replace(/\s+/g, ' ')
}

function retryLastAction() {
  if (lastAction.value) void lastAction.value()
}

onMounted(async () => {
  await loadModelProviders()
  await loadProjects()
  const queryProject = route.query.project || route.query.projectId
  const requestedProject = Array.isArray(queryProject) ? queryProject[0] : queryProject
  if (requestedProject && projects.value.some((item) => item.projectId === requestedProject)) {
    await selectProject(requestedProject)
  }
  if (projects.value.some((item) => isBusyStatus(item.status))) startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>
