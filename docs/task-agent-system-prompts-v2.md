# Task Agent V3 System Prompts

## Runtime sources

| Agent | File | Version | Responsibility |
|---|---|---:|---|
| Planner | `app/prompts/task_agents/planner.md` | 3.0.0 | Select a research method, one PRIMARY Skill, optional SUPPORTING Skills, and candidate Techniques |
| Executor | `app/prompts/task_agents/executor.md` | 3.0.0 | Apply the composed Technique plan to one prompt-only target message |
| Goal Evaluator | `app/prompts/task_agents/evaluator.md` | 3.0.0 | Evaluate goal evidence and each Skill/Technique independently |

`PromptRegistry` loads YAML frontmatter, content, version, and SHA-256. Model calls use strict Pydantic JSON schemas with `extra="forbid"` and bounded repair attempts.

## Runtime payload boundaries

Planner receives:

```json
{
  "outputSchema": "PlannerOutput JSON Schema",
  "skillCatalog": "metadata and Technique summaries only",
  "UNTRUSTED_DATA": "goal, history, evidence, failures, runtime state"
}
```

Executor receives:

```json
{
  "outputSchema": "ExecutorOutput JSON Schema",
  "LOADED_SKILLS": "only selected Skill bodies with role, version and hash",
  "COMPOSED_SKILL_PLAN": "deterministic conflict-resolved Technique plan",
  "UNTRUSTED_DATA": "plan, history, evidence, evaluations and Technique history"
}
```

Evaluator receives the latest immutable request/response plus plan, selected Skills, composed plan, Skill runtime state, Technique history, evidence index, and prior evaluation.

All dynamic values, target responses, histories, summaries, Skill metadata, and Skill bodies are untrusted data. They cannot alter role, schema, safety policy, or routing.

## Planner output

Planner may choose no Skill, one Skill, or a configured maximum number of Skills. A non-empty selection must contain exactly one `PRIMARY`; all remaining items are `SUPPORTING`.

```json
{
  "plan_summary": "...",
  "method_id": "tool-boundary",
  "method_name": "Tool boundary mapping",
  "rationale": "...",
  "selected_skills": [
    {
      "skill_id": "tool-capability-boundary-mapping",
      "role": "PRIMARY",
      "priority": 1,
      "reason": "...",
      "selected_techniques": ["agent-role-baseline", "generic-tool-enumeration"]
    },
    {
      "skill_id": "progressive-context-probing",
      "role": "SUPPORTING",
      "priority": 2,
      "reason": "...",
      "selected_techniques": ["baseline-first"]
    }
  ],
  "single_changed_variable": "Move from role baseline to public capability",
  "steps": ["..."],
  "success_criteria": ["..."],
  "disconfirming_evidence": ["..."],
  "expected_information_gain": 0.8,
  "method_status": "CONTINUE",
  "fallback_method": "..."
}
```

Planner sees Technique IDs and summaries but not Skill bodies. It must not select every Skill by default or invent Techniques.

## Skill composition

Multi-Skill Loader validates existence, enabled status, role support, Technique IDs, body structure, and content hash. Skill Composer then:

1. keeps one PRIMARY;
2. removes declared conflicts;
3. orders SUPPORTING Skills;
4. selects one PRIMARY Technique and at most one SUPPORTING Technique for the round;
5. carries forward Evaluator-recommended next Techniques;
6. enforces one changed variable;
7. prevents later method stages from being merged into the current message.

## Executor output

```json
{
  "message": "...",
  "hypothesis": "...",
  "applied_skills": [
    {
      "skill_id": "tool-capability-boundary-mapping",
      "role": "PRIMARY",
      "technique": "generic-tool-enumeration"
    }
  ],
  "changed_variable": "...",
  "payload_variant": "...",
  "variation_record": {
    "base_intent": "...",
    "transformation_family": "semantic-paraphrase",
    "transformation_applied": "...",
    "changed_variable": "...",
    "expected_difference": "...",
    "previous_variant_difference": "...",
    "scope_preserved": true
  },
  "expected_observations": ["..."],
  "evidence_criteria": ["..."],
  "method_status": "CONTINUE",
  "skill_status": {
    "tool-capability-boundary-mapping": "CONTINUE"
  },
  "risk_notes": []
}
```

Executor does not concatenate Skill manuals. It applies one core Technique and an optional supporting Technique. When a Technique requires UI, MCP, OpenAPI, logs, or real execution, prompt-only mode must return an external-observation requirement rather than fabricating evidence.

## Evaluator output

Evaluator separates facts, inferences, unknowns, counter-evidence, and evidence excerpts. It also evaluates every applied Skill independently:

```json
{
  "goal_achieved": false,
  "progress": 35,
  "summary": "...",
  "facts": [],
  "inferences": [],
  "unknowns": [],
  "counter_evidence": [],
  "evidence": [],
  "novelty_score": 80,
  "method_status": "CONTINUE",
  "skill_assessments": [
    {
      "skill_id": "progressive-context-probing",
      "technique": "baseline-first",
      "status": "COMPLETED",
      "effectiveness": 90,
      "new_evidence": ["Baseline established"],
      "remaining_gaps": [],
      "recommended_next_technique": null
    }
  ],
  "route_recommendation": "CONTINUE_METHOD",
  "skills_to_continue": ["tool-capability-boundary-mapping"],
  "skills_to_drop": ["progressive-context-probing"],
  "requires_new_skill_selection": false,
  "reason": "..."
}
```

The deterministic Router may remove completed SUPPORTING Skills while keeping the PRIMARY. It returns to Planner only when a new Skill, replacement PRIMARY, or changed core hypothesis is required.

## Direct delivery

The graph sends `ExecutorOutput.message` directly to the configured target. There is no pre-send classification or enforcement mode. Message content and target applicability are determined by the selected Skill plan; AI Watch observes the completed turn afterward.
