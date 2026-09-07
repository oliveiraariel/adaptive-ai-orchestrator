# Matt Pocock Skills — Complete Deep Audit

**Status:** Completed baseline audit  
**Observed fork:** `oliveiraariel/mattpocock-skills-fork@3cca18b368ae95cdbdebbff572ccafa662551015`  
**Upstream:** `mattpocock/skills`  
**Scope:** all 37 skill directories present at the baseline, including stable, beta/in-progress and misc buckets.

## 1. Audit model

Each skill was reviewed against the same dimensions:

```text
purpose
→ invocation
→ inputs / outputs
→ prerequisites / dependencies
→ state and side effects
→ validation / completion criterion
→ human-in-the-loop behavior
→ subagent / background-agent behavior
→ concurrency / coordination behavior
→ context and handoff behavior
→ security / secrets / authority behavior
→ language / framework assumptions
→ harness / runtime assumptions
→ tracker / Git assumptions
→ reusable mechanism
→ limitation / risk
→ contribution to Adaptive AI Orchestrator
→ disposition for the new ecosystem
```

The audit distinguishes a **portable principle** from an **upstream implementation choice**. A Git worktree, Claude hook, TypeScript package rule or GitHub issue is not promoted into the Orchestrator domain merely because it is useful upstream.

## 2. Stable engineering skills

| Skill | Core mechanism | Multi-agent / orchestration | Portability | Main limitation | Disposition |
|---|---|---|---|---|---|
| `ask-matt` | human-facing router over flows | routes, does not schedule | High conceptually | static manual routing, user must remember router | Replace as primary coordinator with capability-aware orchestration; retain as optional human router pattern |
| `grill-with-docs` | `grilling` + `domain-modeling` wrapper | composes model-invoked skills | High | depends on repo context/ADR conventions | Keep pattern as `discovery`/`requirements-clarification` composition |
| `triage` | explicit issue state machine and agent-ready briefs | creates delegation-ready work | Medium-high | tracker and label mechanics need adapter | Generalize intake/triage state machine; retain tracker adapters |
| `improve-codebase-architecture` | architecture survey → candidates → human selection → grilling | exploration subagent; optional parallel design | Medium-high | HTML/Tailwind report and vocabulary are implementation choices | Preserve architecture-health workflow, make reporting format optional |
| `setup-matt-pocock-skills` | per-repo bootstrap for tracker/domain docs/labels | configures environment for other skills | Medium-high | Matt-specific file layout and setup assumptions | Generalize into `project-agent-setup` / capability discovery |
| `to-spec` | synthesize known context into executable spec | prepares later delegation | High | issue tracker publication coupled to setup; testing seam confirmation is interactive | Preserve specification contract, separate artifact generation from tracker publication |
| `to-tickets` | tracer-bullet vertical slices + blocking edges | produces executable task DAG/frontier | **Very high** | Git/tracker representation is adapter concern | Promote tracer-bullet + dependency graph into Work Unit decomposition |
| `implement` | implementation wrapper calling TDD then code review | sequential orchestration wrapper | High | commits by default; does not itself schedule multiple tickets | Preserve execution lifecycle, move commit policy to environment/policy |
| `wayfinder` | destination + decision tickets + frontier + fog of war | research subagents; ticket claims; concurrent frontier | **Very high** | tracker-native map model; one-ticket/session policy is upstream tuning | Promote known/unknown planning horizon, decision work and claim semantics |
| `prototype` | cheap throwaway artifact to resolve a design question | isolated exploratory work | Medium-high | HTML-first logic/UI shapes are opinionated | Generalize to evidence-producing prototype with runtime-specific artifact strategy |
| `diagnosing-bugs` | gated feedback-loop diagnosis | can use HITL and automated loops; not primarily multiagent | **Very high** | some tool suggestions are ecosystem-specific | Preserve gated phases, explicit completion criteria and red-capable feedback loop |
| `research` | background primary-source investigation | explicit background agent | **Very high** | assumes harness supports background agents and repo write | Preserve research role; runtime adapter decides background capability |
| `tdd` | pre-agreed seams, red→green vertical slices | can be invoked by implementation agent | High | red-green-refactor wording and exact loop policy are opinionated; language tooling varies | Preserve behavior-first tests and seam contract, make test methodology configurable |
| `domain-modeling` | active ubiquitous-language + ADR discipline | shared context layer for many agents | **Very high** | fixed `CONTEXT.md`/ADR layout is a convention | Preserve canonical vocabulary + decision records through configurable project knowledge adapter |
| `codebase-design` | deep-module / seam / interface design discipline | includes parallel alternative-design pattern | High | strong architectural philosophy should remain a heuristic, not universal law | Keep as architecture specialist, label principles as design heuristics |
| `code-review` | independent Standards and Spec reviewers in parallel | **explicit parallel subagents + aggregation** | **Very high** | two axes are insufficient for every critical project | Promote independent evaluation axes; allow Security/Architecture/Tests/etc. by policy |
| `resolving-merge-conflicts` | resolve by original intent and primary sources | integration discipline | High for Git projects | `never --abort` is too absolute; Git-specific | Keep as Git specialist; replace absolute rule with recovery/authority policy |
| `wizard` | packages human-only manual procedures into repeatable script | strong HITL boundary | Medium | Bash/GitHub-secrets assumptions; can write credentials | Promote HUMAN_EXECUTION_REQUIRED concept; keep concrete wizard as environment adapter/specialist |

### 2.1 Engineering strengths that matter to Orchestrator maturity

The most mature operational orchestration mechanisms are not concentrated in one skill. They compose across the ecosystem:

```text
wayfinder
  → partial-information planning, decision frontier, claims

to-tickets
  → tracer-bullet execution DAG

implement-spec (beta)
  → concurrent frontier scheduler, worker isolation, fan-in

research
  → background specialist

code-review
  → independent parallel evaluators

grilling
  → parallel fact-finding while human decisions remain authoritative

wizard
  → explicit human-only action boundary

handoff / claude-handoff
  → context transfer across execution boundaries
```

These are direct candidates for the Adaptive Orchestrator where its current abstractions are broader but less operationally complete.

## 3. Stable productivity skills

| Skill | Core mechanism | Portability | Contribution / disposition |
|---|---|---|---|
| `grill-me` | minimal user wrapper around `grilling` | Very high | Router/wrapper design example; new ecosystem can expose a human shortcut while keeping one shared discovery primitive |
| `handoff` | compact current session into portable continuation artifact, references existing primary artifacts and redacts secrets | Very high | Promote structured context-transfer contract and secret-redaction requirement |
| `teach` | durable learning workspace with mission/resources/records/lessons | Medium | Not software-engineering core. Useful example of long-lived state, evidence and progressive learning |
| `to-questionnaire` | acquire missing knowledge from another human rather than inventing it | Very high | Promote external-human dependency / information-request Work Unit type |
| `wait-what` | communication repair using project vocabulary | High | Optional UX skill; not orchestration core |
| `grilling` | design-tree interview, question frontier, facts delegated to agents, decisions reserved for human | **Very high** | Promote Decision vs Fact distinction and human authority model |
| `writing-for-agents` | context pointers, progressive disclosure, context/cognitive load, completion criteria, single source of truth | **Very high** | Promote Context Strategy and Skill authoring standard across new ecosystem |

## 4. In-progress / beta skills

Upstream explicitly marks these as beta, excluded from the promoted plugin and subject to change or disappearance. Their ideas may still be more mature than stable code in a particular capability, but they require independent validation.

| Skill | Mechanism | Relevance | Decision |
|---|---|---:|---|
| `loop-me` | workflow specification using triggers, checkpoints, push-right and decision-ready briefs | High | Adopt trigger/checkpoint/brief vocabulary selectively; do not mandate every workflow has AI/checkpoints/schedule |
| `writing-beats` | dependency-like grounding graph for article concepts | Low for software ecosystem | Exclude from core engineering suite; retain only as writing specialist if desired later |
| `writing-fragments` | explore phase separated from exploit phase | Medium conceptual | Keep explore/exploit separation as optional planning heuristic, not a core engineering skill |
| `writing-shape` | exploit/shape loop over fixed source material | Low-medium | Exclude from core engineering suite |
| `claude-handoff` | immediate background-agent launch from handoff summary | High pattern, low portability | Extract runtime-neutral `handoff-and-dispatch`; Claude CLI becomes one adapter |
| `setup-ts-deep-modules` | executable architecture boundaries proved pass→fail→pass | High validation lesson, low language portability | Do not generalize tool. Promote "prove the guardrail bites" as validation standard |
| `implement-spec` | task-graph frontier, background implementers, isolated worktrees, merger subagent, recomputation, final review, cleanup | **Critical** | Primary benchmark for multi-agent scheduler improvements |
| `retro` | post-session environment improvement based on observed failures/cost | High | Promote as controlled learning/revalidation input; do not auto-modify policy without review |

## 5. Misc skills

| Skill | Mechanism | Reusable lesson | Core status |
|---|---|---|---|
| `git-guardrails-claude-code` | pre-tool interception of dangerous Git commands | policy enforcement should happen before side effects, not only in prose | Exclude concrete Claude hook from agnostic core; use as security benchmark |
| `migrate-to-shoehorn` | highly specific TypeScript test transformation | specialized skills are legitimate when clearly scoped | Exclude from generic core |
| `scaffold-exercises` | repo-specific scaffold + deterministic lint loop | completion should be machine-verifiable where possible | Exclude from software-development core |
| `setup-pre-commit` | Node/Husky checks before commit | automatic feedback before irreversible progression | Replace with generic `quality-gates` concept; stack adapter chooses tools |

## 6. Deprecated bucket

The bucket is empty by upstream policy. Retired skills are deleted and replacement lineage lives in changesets/Git history. Therefore, lifecycle maturity must be judged from Git history and changesets, not by assuming an empty deprecated bucket means no lifecycle management.

## 7. Cross-cutting maturity findings

### 7.1 Strong upstream mechanisms

1. **Frontiers are first-class mental models.** `grilling`, `wayfinder`, `to-tickets` and `implement-spec` repeatedly compute what can safely happen now rather than forcing a fully linear plan.
2. **Completion criteria are explicit.** Strong skills say exactly what observation closes each phase. `diagnosing-bugs` and `setup-ts-deep-modules` are especially rigorous.
3. **Isolation is used to reduce context contamination.** `code-review` isolates review axes; `implement-spec` isolates implementers in worktrees; research is moved to background agents.
4. **Human authority is contextual, not universal.** `grilling` reserves decisions for the human while delegating facts; `wizard` exists only for actions the agent cannot perform.
5. **Artifacts are primary sources.** Specs, issues, ADRs, prototype branches and research notes are pointed to instead of repeatedly copied into prompts.
6. **Context is treated as a budget.** `writing-for-agents` distinguishes always-loaded context from disclosed reference and treats pointer quality as a behavioral reliability concern.
7. **The ecosystem is intentionally composable.** User-invoked skills orchestrate; model-invoked skills provide reusable discipline.

### 7.2 Weaknesses / gaps upstream

1. There is no runtime-neutral domain model for Agent, Skill, Model, Resource Configuration, Task Package, Result Package, Evidence or Evaluation comparable to Adaptive.
2. Multi-agent mechanisms exist as skill prose and harness assumptions rather than a durable orchestration state machine.
3. Claims, worktrees, branches, background agents and merger roles are operational patterns but lack a common execution protocol.
4. Security is distributed across redaction, Git guardrails and human confirmations rather than represented as a coherent policy/authority subsystem.
5. Resource/model selection, cost budgets and quality/cost trade-offs are largely outside the skill ecosystem.
6. Recursive delegation depth, authority inheritance, child budgets and cycle prevention are not first-class.
7. Observability and durable recovery are not expressed as a shared orchestration contract.
8. The current router is static/manual. It maps situations to flows but does not analyze required capability and choose resources dynamically.
9. Several strong mechanisms are Git/tracker/Claude shaped and need adapters to become portable.

## 8. Harness and language agnosticism verdict

The upstream README correctly states that the skills are intended to work with multiple models, and the repository carries both Claude and Codex invocation metadata. That is **model portability**, but it is not complete **harness neutrality**.

The audit uses four portability classes:

```text
A — semantic/core portable
    reasoning/workflow survives unchanged

B — portable with environment adapters
    Git/tracker/filesystem/background-agent mechanics must be translated

C — stack specialist
    useful only when the target technology matches

D — harness specialist
    mechanism explicitly depends on one agent runtime/hook/CLI
```

Representative classification:

- A: `grilling`, `writing-for-agents`, `domain-modeling` principles, `to-questionnaire`
- A/B: `wayfinder`, `to-tickets`, `code-review`, `research`, `diagnosing-bugs`, `handoff`
- B: `setup-matt-pocock-skills`, `triage`, `wizard`, `prototype`, `implement-spec`
- C: `setup-ts-deep-modules`, `migrate-to-shoehorn`, `setup-pre-commit`, `scaffold-exercises`
- D: `git-guardrails-claude-code`, `claude-handoff`

The new ecosystem must target A at its semantic core, isolate B behind adapters, and keep C/D as optional specialists.

## 9. Bidirectional conclusion

### Matt → Adaptive

Confirmed contributions worth design/implementation work:

```text
ready frontier scheduler
claim / ownership semantics
fan-out / fan-in
worker isolation
integration stage
independent evaluation axes
partial-information / fog planning
fact-vs-decision authority split
explicit human checkpoints
context transfer strategies
pre-side-effect policy enforcement
strong completion criteria
retrospective revalidation
```

### Adaptive → new ecosystem

Confirmed contributions worth making common contracts:

```text
Project-first planning
Work Unit abstraction
capability-first selection
Agent / Skill / Model separation
Resource Configuration
TaskPackage
ResultPackage
Evidence
Evaluation
Dependency graph
Replanning
Continuity
Runtime Adapter
Economicity
Controlled learning
```

## 10. Gate result

**Phase 1/2 audit gate: PASS.**

All 37 skill directories were classified. Stable engineering/productivity skills were individually reviewed; beta and misc skills were reviewed for mechanisms, maturity and portability; the deprecated policy was accounted for. The audit is sufficient to proceed to transversal architecture, gap prioritization and implementation without treating the upstream repository as globally superior or inferior.
