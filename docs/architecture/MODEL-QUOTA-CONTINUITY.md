# Quota-aware model continuation (Terra → Kimi → Terra)

## Status and operational boundary

This feature is implemented on a feature branch, **not deployed** to the local
OpenClaw Gateway. The Bridge CLI interface is unchanged.

It extends the existing OpenClaw Gateway runtime failover path and the Adaptive
ModelRoutingPolicy. It does **not** authorize direct execution by the owner.

## Normal operation

* The installed `ADAPTIVE_ECONOMY_MODEL=openai/gpt-5.6-terra` and
  `ADAPTIVE_ROUTINE_THINKING=medium` remain the preferred low/routine route.
* When a recognized **renewable** OpenAI quota or 429 error reaches the Gateway
  result boundary and no verified Result Store artifact exists, Adaptive records
  a **5h05** cooldown for that exact model and auth profile.
* A failed GPT worker is handed to a **fresh executor session** on configured
  Kimi K2.7, preserving the Work Unit ID, task context, existing Git workspace,
  Result Store contract and previously accepted work.
* During the cooldown, newly routed Work Units use Kimi instead of the
  exhausted OpenAI model. In-flight Kimi sessions are not forcibly interrupted.
* After the cooldown expires, subsequent new Work Units automatically select
  the configured GPT route again. If quota remains exhausted, a new error
  will start a fresh cooldown. This is a **retry time**, not proof of actual
  quota reset.
* The fallback chain excludes model/auth-profile routes already attempted for
  that Work Unit; this prevents oscillation between Kimi and depleted GPT.
* Existing acceptance, Work Unit recovery, checkpoints and human-approval
  governance are unchanged. **Direct fallback requires explicit human approval**.

## Controls

| Variable | Default | Description |
| --- | --- | --- |
| `ADAPTIVE_QUOTA_CONTINUITY_ENABLED` | `1` | Toggle the durable quota-aware routing |
| `ADAPTIVE_GPT_QUOTA_COOLDOWN_SECONDS` | `18300` | 5h05 retry interval |
| `ADAPTIVE_QUOTA_CONTINUITY_PATH` | `~/.local/state/adaptive-ai-orchestrator/model-quota-cooldowns.json` | Shared, atomic, permission-restricted state |
| `ADAPTIVE_ECONOMY_MODEL` | existing policy/environment | Set to `openai/gpt-5.6-terra` operationally |
| `ADAPTIVE_KIMI_ENABLED` | `1` | Allows Kimi as the alternative |
| `ADAPTIVE_KIMI_AUTH_PROFILE` | existing provider configuration | Must be valid and funded |

The route key hashes provider, model and auth-profile identity; the state file
does not contain credentials or task prompts. File writes are locked and atomic.
The feature does not automatically raise spending limits or purchase capacity.

## Explicit limitations

* Billing failures, daily/weekly/monthly windows and authentication failures
  are **not assumed** to reset after 5h05.
* The feature reacts to **identified Gateway provider failures**. If an executor
  remains indefinitely RUNNING with a falsely fresh heartbeat but no provider
  error, this feature alone does not prove it safe to revoke its lease or
  redistribute work. That separate execution-liveness problem needs verified
  progress/lease fencing, and must not be solved by blind parallel dispatch.
* Autonomous fallback to direct owner execution is intentionally **not added**.
  If multiagent recovery is exhausted, preserve the incident and ask the owner.
* A browser/OpenClaw provider integration test with real credentials was **not**
  performed in the development environment. The CI tests use mocks.

## Validation and rollout

The repository GitHub Actions tests cover persisted cooldown, profile isolation,
budget classification safeguards, delayed return to Terra, repeated failover
cycle prevention, same-Work-Unit handoff, and separate executor sessions.

To activate, review and integrate the feature branch into the **operational
Adaptive checkout**, then confirm active OpenClaw provider configuration.
Do not change the Bridge, `main`, or running Gateway automatically. Protect
active workers during any operational rollout.
