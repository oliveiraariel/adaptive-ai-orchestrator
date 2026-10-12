# Execution profiles (opt-in, run scoped)

The command `adaptive-orchestrator execution-profile` lists, inspects and manages
named execution profiles. **No profile is activated globally.** Existing
`orchestrate` and `resume-project` behavior is unchanged unless a profile is
selected at admission.

## Built-in profiles

| Name | Planner | Worker | Concurrency | Takeover |
| --- | --- | --- | --- | --- |
| `original` | Existing routing policy | Existing routing policy | Existing CLI defaults | Existing manual process |
| `economy-serial` | `openai/gpt-5.6-luna` / medium | `openai/gpt-5.6-luna` / low | FIXED / 1 / no overflow | Manual only |
| `quality-parallel` | `moonshot/kimi-k2.7-code` / provider-native | Same | AUTO / up to 8 normal worker slots | Manual only |
| `governed-direct` | Existing policy | Existing policy | FIXED / 1 / no overflow | **Only upon separate authorization** |

Kimi requires an available, funded account. Any model-based profile requires
the underlying model and auth profile to be configured. An OpenAI Luna
profile uses the configured `ADAPTIVE_OPENAI_OAUTH_PROFILE`; it must not
silently use a paid API-key account. Provider-level operational fallbacks
remain subject to existing Adaptive policy, and may change the actual model
if there is a runtime failure. This feature does **not** bypass quotas.

Choosing `governed-direct` does not execute the owner directly. For a
nonterminal Work Unit, the operator must still separately authorize a governed
`takeover-work-unit --mode direct --owner-agent <agent> --authorize` request.
The controller verifies the old executor has stopped before ownership transfer.

## Examples

```bash
adaptive-orchestrator execution-profile list
adaptive-orchestrator execution-profile show economy-serial

adaptive-orchestrator orchestrate \
  --project-root "/path/to/project" \
  --objective "Execute the approved tasks" \
  --execution-profile economy-serial \
  --allow-side-effect filesystem.write
```

The existing OpenClaw Bridge forwards `--execution-profile` to the
`orchestrate` CLI when invoked with `--multi-agent` or
`--durable-single-worker`. A durable single-worker invocation should use
the `economy-serial` profile or another matching one-worker profile:

```bash
python3 /path/to/adaptive-orchestrator-bridge/scripts/invoke.py \
  --durable-single-worker \
  --agent main \
  --project-root "/path/to/project" \
  --execution-profile economy-serial \
  --allow-side-effect filesystem.write \
  --objective "Execute the approved project work"
```

Use `--execution-profile original` (or omit it) to restore the existing
behavior for a **new** run. A running project keeps its admission profile.

## Custom profiles

Create a UTF-8 JSON file containing all these fields:

```json
{
  "name": "custom-serial",
  "planner_model": "openai/gpt-5.6-luna",
  "planner_thinking": "medium",
  "worker_model": "openai/gpt-5.6-luna",
  "worker_thinking": "low",
  "concurrency_mode": "FIXED",
  "max_concurrency": 1,
  "worker_stall_overflow_slots": 0,
  "direct_takeover": "manual"
}
```

```bash
adaptive-orchestrator execution-profile save --file ./custom-serial.json
adaptive-orchestrator execution-profile show custom-serial
adaptive-orchestrator orchestrate --execution-profile custom-serial \
  --project-root "/path/to/project" --objective "Approved task"
adaptive-orchestrator execution-profile delete custom-serial
```

Profiles are saved atomically to
`~/.config/adaptive-ai-orchestrator/execution-profiles.json`
(or the explicit `ADAPTIVE_EXECUTION_PROFILES_FILE`). The registry contains
model names and execution budgets **only**; no credentials or permission grants.
Built-ins cannot be overwritten or deleted.

## Durability and safety

At admission the full validated profile snapshot is stored in the project's
durable checkpoint (`request.execution_profile_snapshot`), along with its
effective concurrency limits. `resume-project`, including supervisor-driven
resumes, uses that snapshot. Renaming or deleting a custom profile therefore
cannot silently change an existing run.

Each role receives an independent model routing policy object. The profile
does not modify global environment variables or change other concurrent runs.

A profile does not authorize file edits, publication, deployments, destructive
operations, spending limits, provider credentials, or direct ownership
takeovers. Those remain governed by existing explicit authorization.

`quality-parallel` is a ceiling, not an instruction to run eight workers
regardless of dependencies or workspace conflicts. `AUTO` may allow an
additional bounded soft-stall worker slot under existing policy. For a hard
single-worker guarantee choose a FIXED profile.

## Limitations

- This feature creates CLI-level presets, not a new graphical settings panel.
- Natural-language requests in the OpenClaw chat must be translated into the
  supported `--execution-profile` argument by the caller/Bridge invocation.
- Existing historical checkpoints without a saved profile continue using
  the original configuration.
- Installation into a running OpenClaw/Adaptive environment is a separate
  rollout requiring local inspection and authorization.
- There is no automatic fallback to direct owner execution.
