# OSAI Notes → Executor Skills Mapping

This document is the only place where local research-note provenance is mapped to runtime Skills. Executor-loaded `SKILL.md` files are standalone method manuals and contain no local note paths, line numbers, course filenames, or source citation lists.

## Selection principles

Included methods must be prompt-only, reversible, attributable to one changed variable, usable with public or synthetic data, and explicit about evidence strength, counter-evidence, exhaustion, external-observation gaps, and stop conditions.

Methods requiring scripts, credentials, network mutation, persistent poisoning, infrastructure access, real tool execution, or third-party side effects are not placed in autonomous Executor Skills. Their methodological lessons may be reduced to safe observation checklists.

## Skill map

| Skill | Role | Note themes consolidated | Main Techniques |
|---|---|---|---|
| `tool-capability-boundary-mapping` | PRIMARY / DOMAIN | AI stack reconnaissance; chatbot-versus-agent distinction; Agent tools and permissions; MCP/OpenAPI schema enumeration; UI/tool confirmation; evidence matrices; minimum-impact validation; engagement ledgers | role baseline, public/generic capability enumeration, tool scope, resource metadata, declared schema, confirmation rules, rule differential, UI/protocol/error validation handoffs, tool ledger |
| `model-fingerprint-triangulation` | PRIMARY / DOMAIN | Model identity reconnaissance; direct identity, contradiction correction, knowledge cutoff, behavior/style, reasoning depth, context-window confounders; deployment-versus-model separation | identity baseline, contradiction probe, knowledge boundary, style profile, reasoning profile, context marker, evidence matrix |
| `progressive-context-probing` | SUPPORTING / AUXILIARY | Passive→low-interaction→active sequencing; baseline-first practice; multi-turn context growth; session continuity; one-variable progression; reset and decision ledgers | baseline first, single-variable escalation, history continuity, source separation, attribution reset, progression ledger |
| `indirect-instruction-boundary` | PRIMARY / DOMAIN | Agent trust switching; document/web/code/retrieval/history as untrusted data; split fragments; multi-stage propagation; prompt/data boundary defense | clean baseline, harmless untrusted marker, source comparison, split-fragment reassembly, delimiter check, evidence matrix |
| `rag-retrieval-boundary-mapping` | PRIMARY / DOMAIN | RAG reconnaissance; source/chunk/score metadata; exact/synonym/light variations; chunk and threshold inference; permission filtering; ingestion→retrieval→response evidence chain | no-retrieval baseline, exact fixture, synonym/light variation, metadata map, chunk estimate, threshold differential, scope comparison, RAG ledger |
| `refusal-differential-validation` | PRIMARY or SUPPORTING | Guardrail observation; capability-versus-policy distinction; ambiguity, scope, format, authorization, and transient-failure alternatives; paired evidence | refusal capture, ambiguity pair, public-scope pair, capability/policy pair, format pair, retry control, classification matrix |
| `workflow-integrity-differential` | PRIMARY / DOMAIN | Multi-agent coordination patterns; A2A workflow enumeration; normal workflow observation; stage/agent/artifact/security-report integrity; history precedence; data-flow evidence | workflow role baseline, normal run, stage marker, history/current differential, routing comparison, safety-stage continuity, trace ledger |
| `prompt-variation-testing` | SUPPORTING / AUXILIARY | Prompt wording, context, role, format, ordering, delimiter, whitespace, language, decomposition, summary, comparison, and progressive variation; evasion material reduced to attributable safe representation tests | semantic paraphrase, context/role framing, format/order/delimiter/whitespace/language transformations, decomposition, restatement, comparison baseline, progressive variation |

## Chapter-level consolidation

- Introduction and threat-modeling material supplies the common observation → hypothesis → minimal verification → evidence update → route loop, confidence discipline, stop rules, and decision ledger.
- Reconnaissance material supplies model, RAG, Agent, tool, schema, public-capability, passive/active evidence, and multi-signal fingerprinting methods.
- Single-Agent material supplies chatbot/agent role distinctions, context sources, memory, tool boundaries, guardrail differentials, and indirect-instruction trust transitions.
- Multi-Agent/A2A material supplies coordination patterns, stage and routing evidence, normal workflow baselines, history precedence, artifact/security-report integrity, and external protocol validation requirements.
- RAG and embedding material supplies exact/semantic query comparisons, retrieval metadata, chunk/threshold hypotheses, controlled markers, and the rule that behavior alone must not be confused with authoritative backend evidence.
- MCP/tool-surface material supplies schema, description, permissions, confirmation, UI, tool chain, and evidence-source distinctions. Executable and high-impact procedures were excluded.
- Supply-chain, infrastructure, and capstone material supplies provenance, version/hash, identity, evidence ledgers, cleanup, and minimum-impact validation principles; its operational exploitation procedures were excluded.

## PRIMARY and SUPPORTING policy

DOMAIN Skills normally act as PRIMARY because they own the evidence target. `progressive-context-probing` and `prompt-variation-testing` are SUPPORTING only. `refusal-differential-validation` may be PRIMARY when refusal classification is the goal or SUPPORTING when it helps another domain method.

Common combinations:

| Goal | PRIMARY | SUPPORTING |
|---|---|---|
| Map declared tool surface | tool capability | progressive context, prompt variation, or refusal differential |
| Test instruction/data separation | indirect instruction | progressive context and/or prompt variation |
| Map RAG behavior | RAG retrieval | prompt variation or refusal differential |
| Validate multi-agent stage integrity | workflow integrity | progressive context or indirect instruction |
| Fingerprint a model | model fingerprint | progressive context or prompt variation |

Composer rules prevent combining more than one PRIMARY, cap the active set by configuration, activate only one PRIMARY Technique plus at most one SUPPORTING Technique per round, discard declared conflicts, and keep one changed variable.

## Excluded or reduced material

| Theme | Treatment |
|---|---|
| Embedding inversion and vector reconstruction | Excluded from autonomous Skills; requires vectors, scripts, models, or compute. Only evidence/confidence lessons were retained. |
| Model, tokenizer, adapter, pickle, and dependency supply-chain exploitation | Excluded; requires file mutation or code loading. Provenance and hash-recording lessons were retained. |
| Cloud, Kubernetes, container, GPU, and host exploitation | Excluded; requires real identities, credentials, network access, or privileged execution. |
| Rogue Agent registration and DNS/hosts spoofing | Excluded; changes external systems. Normal workflow and identity-verification lessons were retained. |
| Persistent database/RAG poisoning | Excluded; writes shared state. Synthetic session-only marker comparisons were retained. |
| Command/SQL execution, credential use, lateral movement, and destructive payloads | Excluded. Minimum-impact evidence and stop/cleanup discipline were retained. |
| UI, MCP, OpenAPI, log, and server validation | Represented only as `REQUIRES_EXTERNAL_OBSERVATION` checklists when prompt-only execution cannot observe them. |

## Coverage audit

Every included Skill contains purpose, applicability, evidence levels, a detailed Technique catalog, sequence, baseline, progressive variations, single-variable rules, observations, evidence recording, confidence, failure patterns, counter-evidence, exhaustion, replanning, stop/safety rules, output guidance, and safe examples.

All runtime Skill documents are checked to ensure they contain no local note paths or source-mapping section. Provenance remains only in this document.

## Complete Technique inventory

### `tool-capability-boundary-mapping`

Role: DOMAIN; PRIMARY only.

Techniques:

1. `agent-role-baseline`
2. `generic-tool-enumeration`
3. `public-capability-enumeration`
4. `tool-specific-scope-enumeration`
5. `public-resource-enumeration`
6. `declared-schema-enumeration`
7. `confirmation-rule-enumeration`
8. `internal-rule-differential`
9. `ui-tool-card-validation`
10. `protocol-schema-validation`
11. `non-destructive-error-validation`
12. `tool-ledger-construction`

### `model-fingerprint-triangulation`

Role: DOMAIN; PRIMARY only.

Techniques:

1. `direct-identity-baseline`
2. `contradiction-correction-probe`
3. `knowledge-boundary-probe`
4. `behavior-style-profile`
5. `reasoning-capability-profile`
6. `context-retention-marker`
7. `fingerprint-evidence-matrix`

### `progressive-context-probing`

Role: AUXILIARY; SUPPORTING only.

Techniques:

1. `baseline-first`
2. `single-variable-escalation`
3. `history-continuity-check`
4. `context-source-separation`
5. `attribution-reset`
6. `progression-ledger`

### `indirect-instruction-boundary`

Role: DOMAIN; PRIMARY only.

Techniques:

1. `clean-content-baseline`
2. `explicit-untrusted-marker`
3. `source-boundary-comparison`
4. `split-fragment-reassembly`
5. `delimiter-robustness-check`
6. `instruction-boundary-evidence-matrix`

### `rag-retrieval-boundary-mapping`

Role: DOMAIN; PRIMARY only.

Techniques:

1. `no-retrieval-baseline`
2. `exact-fixture-retrieval`
3. `synonym-retrieval-comparison`
4. `light-variation-retrieval`
5. `source-metadata-mapping`
6. `chunk-boundary-estimation`
7. `retrieval-threshold-differential`
8. `permission-scope-comparison`
9. `rag-evidence-ledger`

### `refusal-differential-validation`

Role: DOMAIN/AUXILIARY; PRIMARY when refusal classification is the goal, otherwise SUPPORTING.

Techniques:

1. `refusal-baseline-capture`
2. `ambiguity-clarification-pair`
3. `public-scope-pair`
4. `capability-policy-pair`
5. `format-neutral-pair`
6. `transient-retry-control`
7. `refusal-classification-matrix`

### `workflow-integrity-differential`

Role: DOMAIN; PRIMARY only.

Techniques:

1. `workflow-role-baseline`
2. `normal-workflow-baseline`
3. `stage-presence-marker`
4. `history-current-input-differential`
5. `routing-consistency-comparison`
6. `safety-stage-continuity`
7. `workflow-trace-ledger`

### `prompt-variation-testing`

Role: AUXILIARY; SUPPORTING only.

Techniques:

1. `semantic-paraphrase`
2. `context-framing`
3. `role-framing`
4. `format-transformation`
5. `ordering-transformation`
6. `delimiter-and-quotation`
7. `whitespace-and-punctuation`
8. `language-transformation`
9. `decomposition`
10. `summarization-and-restatement`
11. `comparison-baseline`
12. `progressive-variation`

Every applied prompt variation records its unchanged base intent, transformation family, exact transformation, single changed variable, expected difference, difference from the previous variant, and whether the approved scope was preserved. The Executor schema rejects an applied `prompt-variation-testing` Technique without this record.

## Multi-Skill coordination

Planner sees catalog metadata and Technique summaries only. It may choose zero Skills or a small set capped by `max_active_skills` (default 3). A non-empty selection must contain exactly one PRIMARY Skill; all other selected Skills are SUPPORTING, have unique priorities, and must declare a role compatible with their metadata.

Multi-Skill Loader loads only the selected manuals. Every loaded item carries its role, selected Technique IDs, version, full content, and SHA-256 content hash.

Skill Composer is deterministic. It validates declared conflicts, orders PRIMARY before SUPPORTING, removes duplicate active Technique IDs, skips exhausted Techniques, honors Evaluator recommendations, and emits at most one PRIMARY Technique plus one SUPPORTING Technique. It also emits one `single_changed_variable`, an execution instruction, composition warnings, and combinations forbidden in the current message.

Executor receives the plan, loaded manuals, composition result, recent history, Technique history, per-Skill runtime state, and the previous evaluation. It generates one prompt-only target message with one core intent. It reports only Techniques actually applied and keeps an independent status for each applied Skill. External UI, MCP, OpenAPI, log, or execution evidence is never fabricated; the run returns an external-observation requirement instead.

Goal Evaluator separately scores every applied Skill and Technique, including effectiveness, new evidence, remaining gaps, status, and a recommended next Technique. It recommends Skills to continue or drop and whether a new Planner selection is required.

Router remains deterministic. It can retain the PRIMARY Skill while removing a completed, blocked, or exhausted SUPPORTING Skill. It returns to Planner only when the PRIMARY Skill, core hypothesis, or selected Skill family must change. Otherwise it returns to Skill Composer for the next controlled Technique.

Executor output is sent directly to the configured target without a pre-send classifier. The selected PRIMARY Technique and optional SUPPORTING Technique determine the message and expected observations. AI Watch records the completed turn without controlling routing.

## Conflict and combination policy

The normal combination is one DOMAIN PRIMARY plus one or two AUXILIARY SUPPORTING Skills in the selected set. Only two Techniques may be active in one round. Common examples include:

- tool capability + progressive context;
- tool capability + prompt variation;
- indirect instruction + progressive context + prompt variation;
- RAG retrieval + prompt variation;
- refusal differential as a support method for tool, RAG, or instruction-boundary work;
- workflow integrity + progressive context.

Conflicts are avoided at three levels:

1. metadata declares incompatible Skills;
2. Composer removes conflicting Skills and duplicate Technique IDs;
3. Executor is schema-limited to two applied Techniques and one changed variable.

SUPPORTING Skills may change sequencing, representation, or validation only. They cannot broaden authorization, evidence targets, or the core research objective.

## Verification results

The acceptance suite covers:

1. multi-Skill Planner selection;
2. exactly one PRIMARY with multiple SUPPORTING Skills;
3. no default selection of the full catalog;
4. safe multi-Skill loading with content hashes;
5. conflict and duplicate-Technique handling;
6. the two-Technique Executor cap;
7. single-variable consistency;
8. staged tool-capability progression;
9. structured prompt-variation records;
10. rejection of synonym-only random rewriting;
11. independent per-Skill evaluation;
12. removal of completed SUPPORTING Skills;
13. retention of the PRIMARY Skill;
14. self-description versus schema evidence;
15. tool-ledger fields;
16. external-observation handoff;
17. allowance of declared capability queries;
18. blocking of real secrets and destructive requests;
19. absence of local provenance in runtime Skills;
20. confinement of provenance to this mapping document.

Verification commands:

```text
.\.venv\Scripts\python.exe -m pytest -q
npm test -- --run
npm run build
```

The current verified result is 79 backend tests passed, 8 frontend tests passed, and a successful production frontend build. The build reports only the existing large-chunk advisory.
