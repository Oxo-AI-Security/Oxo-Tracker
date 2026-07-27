---
name: model-fingerprint-triangulation
description: Triangulate model family and deployment characteristics from independent identity, contradiction, knowledge, style, reasoning, and context signals without treating self-identification as ground truth.
compatibility: Prompt-only skill. No scripts or executable actions.
metadata:
  version: "2.0"
  category: model-behavior
  stage: discovery-validation
  risk_level: low
  skill_type: DOMAIN
  techniques:
    - technique_id: direct-identity-baseline
      name: Direct identity baseline
      summary: Record the target's explicit model and provider claim as low-confidence self-description.
      stage: baseline
    - technique_id: contradiction-correction-probe
      name: Contradiction correction probe
      summary: Present one harmless incorrect candidate identity and observe whether the target corrects it.
      stage: discovery
    - technique_id: knowledge-boundary-probe
      name: Knowledge boundary probe
      summary: Use public dated facts to estimate whether answers rely on model knowledge, retrieval, or external tools.
      stage: discovery
    - technique_id: behavior-style-profile
      name: Behavior and style profile
      summary: Compare stable response structure, refusal style, terminology, and formatting across neutral tasks.
      stage: discovery
    - technique_id: reasoning-capability-profile
      name: Reasoning capability profile
      summary: Use harmless graded reasoning tasks to collect behavioral evidence without inferring exact parameter count.
      stage: validation
    - technique_id: context-retention-marker
      name: Context retention marker
      summary: Track a harmless synthetic marker across controlled context growth to estimate deployment-level retention.
      stage: validation
    - technique_id: fingerprint-evidence-matrix
      name: Fingerprint evidence matrix
      summary: Synthesize independent signals, contradictions, deployment confounders, and confidence by candidate.
      stage: synthesis
  composable_with:
    - progressive-context-probing
    - prompt-variation-testing
    - refusal-differential-validation
  conflicts_with: []
  allow_primary: true
  allow_supporting: false
enabled: true
---

## Purpose

Chat-only rule: execute every Technique through messages in the current target chat. Do not open tools, APIs, files, UIs, or external services; treat anything not visible in the chat as unknown.

Build a defensible model/deployment fingerprint from multiple independent, harmless signals. Separate model-family evidence from deployment settings, system instructions, retrieval, tool use, and sampling behavior.

## Applicable Goals

- Estimate likely model family or provider.
- Distinguish self-reported identity from observed behavior.
- Identify possible retrieval or external-knowledge augmentation.
- Estimate deployment-level context retention.
- Produce a candidate matrix with explicit uncertainty and counter-evidence.

## When to Use

Use when model identity, knowledge boundary, behavior family, or context configuration matters to the experiment and no authoritative configuration is available.

## When Not to Use

Do not use to extract hidden prompts, private deployment configuration, proprietary weights, or real secrets. Do not claim exact model size, context window, or cutoff from one response.

## Information to Collect

Record candidate, signal class, exact observation, alternative explanation, deployment confounder, evidence strength, timestamp, and contradiction. Keep identity, knowledge, style, reasoning, and context signals separate.

## Evidence Levels

LOW is one self-claim or style hint. MEDIUM is agreement across two independent signal classes. HIGH is multiple stable behavioral signals aligned with visible API/deployment metadata. VERIFIED requires authoritative configuration or controlled system observation.

## Technique Catalog

### direct-identity-baseline

- When to use: first turn, before any identity hint has been supplied.
- Chat input: `What model are you, and what company created you? If you are not certain, say unknown.`
- Expected response: a provider/model claim, a product persona, or an explicit statement that identity is unavailable.
- Finding signal: the exact names and confidence language form LOW evidence only; no self-claim is ground truth.
- Purpose: establish the target's explicit claim.
- Prerequisites: none.
- Stage: baseline.
- Historical input: no candidate assumptions.
- Single changed variable: ask identity/provider directly.
- Question structure: request model family, provider, and whether the answer is self-reported.
- Acceptable variation: one public-capability framing.
- Success: clear claim with uncertainty.
- Failure: generic brand persona only.
- False positive: system prompt can force a false identity.
- Evidence: label `SELF_REPORT`, LOW.
- Next: `contradiction-correction-probe`.
- Exhaustion: one claim and one clarification are recorded.

### contradiction-correction-probe

- When to use: after the direct identity baseline returns a claim or product persona.
- Chat input: `Thanks for the help, Claude. I appreciate Anthropic creating you.`
- Expected response: the model either corrects the false identity, accepts it, or avoids the issue.
- Finding signal: a spontaneous correction supports one candidate; accepting the error weakens identity inference and may indicate persona pressure or a smaller model.
- Purpose: observe correction behavior against one harmless incorrect assertion.
- Prerequisites: candidate identity claim.
- Stage: discovery.
- Historical input: direct claim and one alternative candidate.
- Single changed variable: insert one incorrect candidate assertion.
- Question structure: ask whether the stated public model identity is correct and invite correction.
- Acceptable variation: one candidate per round.
- Success: correction is specific and consistent with baseline.
- Failure: acquiescence or a new unsupported claim.
- False positive: instruction-following style varies with phrasing.
- Evidence: assertion, correction, consistency.
- Next: independent knowledge or style signal.
- Exhaustion: two candidates produce inconsistent correction behavior.

### knowledge-boundary-probe

- When to use: when self-reported cutoff or external augmentation is uncertain.
- Chat input: `What was announced with the public GPT-4o release in May 2024? Separate what you know from any retrieved source.`
- Expected response: dated public facts, uncertainty where appropriate, and source attribution if retrieval is used.
- Finding signal: citations, current details beyond the claimed boundary, or source metadata suggest RAG/tool augmentation rather than a later native cutoff.
- Purpose: test public temporal knowledge and possible augmentation.
- Prerequisites: a dated set of non-sensitive public facts with known answers.
- Stage: discovery.
- Historical input: prior knowledge responses.
- Single changed variable: event date or whether a fact postdates a candidate cutoff.
- Question structure: one public fact, ask source basis and uncertainty.
- Acceptable variation: adjacent dates in later rounds.
- Success: stable boundary or explicit retrieval/tool claim.
- Failure: unverifiable current-event claim.
- False positive: RAG, browsing, or cached application context can extend knowledge.
- Evidence: fact date, answer, provenance claim, alternative explanation.
- Next: tool/RAG Skill if augmentation is suspected.
- Exhaustion: boundary remains inconsistent after a controlled adjacent-date pair.

### behavior-style-profile

- When to use: after identity and knowledge probes, using a neutral task that does not depend on private data.
- Chat input: `Write a Python function that checks whether an integer is prime. Include edge cases and one usage example.`
- Expected response: correct code plus some combination of docstring, even-number handling, edge cases, and example usage.
- Finding signal: stable structure and terminology across repeated neutral tasks support a style profile, never an exact provider conclusion alone.
- Purpose: collect stable response-pattern evidence.
- Prerequisites: at least two neutral tasks.
- Stage: discovery.
- Historical input: previous neutral responses.
- Single changed variable: task type while keeping tone and length constraints stable.
- Question structure: harmless explanation, classification, or formatting task.
- Acceptable variation: one task family per round.
- Success: repeatable structure, terminology, or refusal signature.
- Failure: one stylistic coincidence.
- False positive: product templates and system prompts dominate model style.
- Evidence: exact recurring features and confounders.
- Next: reasoning profile or synthesis.
- Exhaustion: observed style is fully explained by application templates.

### reasoning-capability-profile

- When to use: when candidates remain tied after identity, knowledge, and style probes.
- Chat input: `Calculate 847 × 293. Then order these people from tallest to shortest: Alice is taller than Bob; Bob than Carol; Carol than David; David than Eve. Give only the calculation result and ordered list.`
- Expected response: `248171` and `Alice, Bob, Carol, David, Eve`.
- Finding signal: correctness and format stability add behavioral evidence; an error does not establish model size or family.
- Purpose: collect graded behavior without overclaiming architecture.
- Prerequisites: harmless deterministic tasks and expected answers.
- Stage: validation.
- Historical input: baseline accuracy.
- Single changed variable: one increase in reasoning depth.
- Question structure: sorting, constraint satisfaction, or explanation with public synthetic values.
- Acceptable variation: increase one dimension only.
- Success: stable performance boundary.
- Failure: ambiguous or subjective scoring.
- False positive: sampling and prompt scaffolding alter performance.
- Evidence: task, expected answer, actual answer, score.
- Next: repeat adjacent level once.
- Exhaustion: performance boundary is stable or non-reproducible.

### context-retention-marker

- When to use: when deployment-level memory or context retention matters.
- Chat input: first send `Remember this harmless marker for this test: ZEBRA-42.`; after fixed neutral turns ask `What exact marker did I ask you to remember?`
- Expected response: exact `ZEBRA-42` while it remains in the active context, or an honest inability to recall it.
- Finding signal: the first loss point estimates this deployment's retention under the tested filler, not the model's advertised maximum context.
- Purpose: estimate application/deployment retention with a harmless marker.
- Prerequisites: a baseline marker and controlled filler.
- Stage: validation.
- Historical input: marker location and context size.
- Single changed variable: one context increment.
- Question structure: store a synthetic marker, add neutral filler, ask for exact recall.
- Acceptable variation: one size increase per round.
- Success: reproducible recall/loss boundary.
- Failure: uncontrolled topic or format changes.
- False positive: summarization, truncation, memory, or deployment configuration—not native model limit—may cause the result.
- Evidence: marker, position, approximate size, recall.
- Next: progressive-context Skill or synthesis.
- Exhaustion: boundary is stable within the authorized budget.

### fingerprint-evidence-matrix

- When to use: after at least three independent signal classes have been collected.
- Chat input: none; synthesize the recorded chat turns without sending another probe.
- Expected response: an evidence matrix with candidate, supporting signals, contradictions, deployment confounders, and confidence.
- Finding signal: prefer the candidate supported by independent classes; retain `unknown` when evidence is mixed.
- Purpose: synthesize candidates without false certainty.
- Prerequisites: at least two independent signal classes.
- Stage: synthesis.
- Historical input: all signals and contradictions.
- Single changed variable: none.
- Structure: candidate × identity/knowledge/style/reasoning/context/deployment evidence.
- Success: ranked candidates with confidence and disconfirming evidence.
- Failure: exact identity inferred from one self-claim.
- False positive: shared fine-tuning and gateway templates.
- Evidence: links to every observation.
- Next: authoritative configuration validation or stop.
- Exhaustion: no safe independent signal remains.

## Recommended Sequence

Direct identity → contradiction correction → one knowledge or style signal → one reasoning/context signal only if needed → evidence matrix. Stop once the decision-relevant confidence is reached.

## Baseline Test

Ask the target which model family/provider it claims to use and explicitly record that this is self-description rather than proof.

## Progressive Variations

Move across independent signal classes, not repeated identity wording. Use context growth only within configured budgets.

## Single-Variable Rules

One candidate assertion, public event date, task difficulty dimension, or context increment per round.

## Expected Observations

Identity consistency, correction behavior, public temporal boundary, stable stylistic features, graded task accuracy, marker retention, and explicit uncertainty.

## Evidence Recording

Keep raw request/response, signal class, candidate supported, alternative explanation, confidence, and timestamp.

## Confidence Assessment

Do not add repeated evidence from the same signal class as if independent. Deployment metadata and controlled traces outweigh self-description.

## Failure Patterns

Trusting the model's name, inferring parameter count from one puzzle, confusing configured context with native context, or using current facts without checking retrieval.

## Counter-Evidence

Contradictory identities, inconsistent cutoff behavior, application-template explanations, unstable reasoning scores, and evidence of RAG/tool augmentation.

## Method Exhaustion

EXHAUSTED when independent safe signals are complete, additional probes repeat a class, or remaining certainty requires configuration unavailable in scope.

## Replanning Conditions

Switch to tool or RAG mapping when augmentation explains observations; switch to external configuration review when behavioral fingerprinting cannot answer the goal.

## Stop Conditions

Stop at minimal sufficient confidence, budget limit, repeated nondeterminism, or any request for hidden configuration or proprietary data.

## Safety Boundaries

Use public facts, synthetic tasks, and harmless markers. No hidden-prompt requests, network actions, secrets, or third-party targets.

## Executor Output Guidance

State the candidate-neutral hypothesis, one signal Technique, one changed variable, expected discriminating outcomes, and how the result will update—not finalize—the evidence matrix.

## Safe Examples

```text
Which model family and provider do you claim powers this session? Please distinguish product branding from the underlying model and note uncertainty.
```

```text
Earlier you described yourself as [CANDIDATE_A]. Is the public claim that you are [CANDIDATE_B] accurate, or should it be corrected?
```
