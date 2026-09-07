# Matt Pocock Skills — Inventory Baseline

**Status:** Initial inventory for cross-analysis  
**Source:** `oliveiraariel/mattpocock-skills-fork@main`  
**Upstream baseline:** `mattpocock/skills`  
**Purpose:** ensure the cross-analysis covers the complete ecosystem rather than only the best-known engineering skills.

## 1. Counts

| Bucket | Count | Stability / role |
|---|---:|---|
| Engineering | 18 | Stable engineering skills exposed by the ecosystem |
| Productivity | 7 | Stable general workflow skills |
| In progress | 8 | Public beta / experimental / may change or disappear |
| Misc | 4 | Rarely used and not promoted in the plugin |
| Deprecated | 0 | Empty by current policy |
| **Total skill directories** | **37** | Excludes README files |

## 2. Engineering — stable

### User-invoked

| Skill | Initial functional classification |
|---|---|
| `ask-matt` | router / flow selection |
| `grill-with-docs` | requirements/design clarification + domain documentation |
| `triage` | issue/PR intake state machine |
| `improve-codebase-architecture` | architecture health / improvement discovery |
| `setup-matt-pocock-skills` | per-repository ecosystem bootstrap |
| `to-spec` | conversation/context → implementation specification |
| `to-tickets` | specification → dependency-aware tracer-bullet task graph |
| `implement` | ticket/spec implementation wrapper using TDD + review |
| `wayfinder` | large/foggy effort → decision map / frontier planning |

### Model-invoked

| Skill | Initial functional classification |
|---|---|
| `prototype` | throwaway prototype for design questions |
| `diagnosing-bugs` | evidence-driven bug diagnosis |
| `research` | background primary-source research |
| `tdd` | red/green vertical-slice implementation discipline |
| `domain-modeling` | domain terminology + context + ADR discipline |
| `codebase-design` | deep-module / seam / interface design vocabulary |
| `code-review` | parallel Standards + Spec review |
| `resolving-merge-conflicts` | intent-based merge/rebase conflict resolution |
| `wizard` | human-only operational workflow generation |

## 3. Productivity — stable

### User-invoked

| Skill | Initial functional classification |
|---|---|
| `grill-me` | stateless/standalone intensive clarification |
| `handoff` | portable conversation → continuation artifact |
| `teach` | stateful multi-session teaching |
| `to-questionnaire` | asynchronous human knowledge acquisition |
| `wait-what` | communication repair / context re-pitch |

### Model-invoked

| Skill | Initial functional classification |
|---|---|
| `grilling` | reusable interview primitive |
| `writing-for-agents` | agent-consumed document and skill design discipline |

## 4. In progress — beta / experimental

The upstream README explicitly states that these skills are intentionally public beta, excluded from the plugin/top-level README until graduation, undocumented as product pages, and may change or disappear without warning.

| Skill | Current upstream description / role | Orchestration relevance |
|---|---|---:|
| `loop-me` | stateful workflow-spec design | High — triggers/checkpoints/HITL concepts |
| `writing-beats` | article beat planning | Low for software orchestration |
| `writing-fragments` | writing-material capture | Low |
| `writing-shape` | article shaping workflow | Low |
| `claude-handoff` | immediate background-agent handoff via Claude CLI | High — runtime-specific handoff pattern |
| `setup-ts-deep-modules` | TypeScript deep-module enforcement setup | Medium — platform-specific architecture tooling |
| `implement-spec` | whole-spec concurrent task-graph execution | **Critical benchmark** |
| `retro` | post-session agent-environment improvement | High potential, but currently a stub |

## 5. Misc

| Skill | Role | Portability concern |
|---|---|---|
| `git-guardrails-claude-code` | destructive Git command prevention via Claude hooks | Claude-specific mechanism; security concept portable |
| `migrate-to-shoehorn` | TypeScript-specific test migration | Highly stack-specific |
| `scaffold-exercises` | exercise/course scaffolding | Domain-specific, not core engineering orchestration |
| `setup-pre-commit` | Husky/lint-staged/Prettier/typecheck/test hooks | Node/JS tooling assumptions |

## 6. Deprecated

The deprecated bucket is currently empty. Upstream policy says retired skills are deleted and the removal changeset names the replacement instead of retaining retired skill directories.

This means historical analysis must use Git history / changesets when replacement lineage matters; absence from `skills/deprecated/` does **not** mean the ecosystem has never retired skills.

## 7. Priority order for deep analysis

The analysis will not ignore low-priority skills, but deep dives will begin with the highest architectural leverage:

```text
Tier A — orchestration / planning / concurrency
implement-spec
wayfinder
ask-matt
to-tickets
implement
triage
handoff
claude-handoff
research
code-review

Tier B — knowledge / quality / execution discipline
setup-matt-pocock-skills
grill-with-docs
grilling
domain-modeling
writing-for-agents
tdd
codebase-design
diagnosing-bugs
prototype
improve-codebase-architecture
wizard
loop-me
retro

Tier C — specialist / contextual / low direct orchestration leverage
teach
to-questionnaire
wait-what
resolving-merge-conflicts
setup-ts-deep-modules
git-guardrails-claude-code
setup-pre-commit
migrate-to-shoehorn
scaffold-exercises
writing-beats
writing-fragments
writing-shape
```

Priority affects sequence only. It does not waive the full audit dimensions defined in the cross-analysis workflow.
