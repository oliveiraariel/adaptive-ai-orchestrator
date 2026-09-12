# Policy Activation Runbook

## Why this runbook exists

A routing-policy code change is not complete merely because the repository,
environment variables and unit tests are correct.

Adaptive and OpenClaw have two related but distinct control planes:

```text
Adaptive-dispatched workers
    -> ModelRoutingPolicy
    -> ResourceConfiguration
    -> OpenClawGatewayClient
    -> provider/model@auth-profile

Manually created OpenClaw owner session
    -> OpenClaw session model/account selection
    -> per-agent auth order
    -> session-level pins / last-good state
```

A policy can therefore be correct for workers while a manually-created owner
session still uses a different account or credential.

The incident that motivated this runbook was:

```text
intended:
GPT-5.6 Luna + ChatGPT OAuth + Low

observed:
GPT-5.6 Luna + OpenAI Platform API-key
-> "You have no credits remaining"
```

The missing activation step was the OpenClaw **per-agent OpenAI auth order**.
Setting `ADAPTIVE_OPENAI_OAUTH_PROFILE` configured Adaptive worker dispatch, but
did not by itself force a manually-created owner session to prefer that OAuth
profile.

## Required activation sequence

Use this sequence whenever a model/provider/auth policy changes.

### 1. Update the local Adaptive code first

```bash
cd "/home/ariel/Área de trabalho/VSCode/Git/adaptive-ai-orchestrator"
git switch main
git pull --ff-only origin main
git log -1 --oneline
```

Do not apply runtime settings for code that has not yet been pulled locally.

### 2. Inspect available auth profiles for the target owner agent

Example for OpenAI:

```bash
openclaw models auth list --provider openai --agent sgfp
```

Identify the intended **profile ID**, not a secret token.

For ChatGPT OAuth, expect an entry shaped like:

```text
openai:<account-identifier> [openai/oauth]
```

Do not use an API-key profile when the policy intends ChatGPT subscription OAuth.

### 3. Set the owner agent's provider auth order explicitly

Example:

```bash
openclaw models auth order set \
  --provider openai \
  --agent sgfp \
  "openai:<oauth-profile-id>"
```

This prevents Automatic Account Selection from choosing another eligible OpenAI
profile such as an API-key backup.

### 4. Verify the auth order before continuing

```bash
openclaw models auth order get \
  --provider openai \
  --agent sgfp
```

Do not proceed until the intended OAuth profile is the effective explicit order.

### 5. Apply Adaptive environment policy

For the current economy-first policy, the important settings are:

```text
ADAPTIVE_KIMI_ENABLED=0|1
ADAPTIVE_STRONG_MODEL=moonshot/kimi-k2.7-code
ADAPTIVE_ECONOMY_MODEL=openai/gpt-5.6-luna
ADAPTIVE_CODE_SPECIALIST_MODEL=moonshot/kimi-k2.7-code
ADAPTIVE_ROUTINE_THINKING=low
ADAPTIVE_OPENAI_OAUTH_PROFILE=<oauth-profile-id>
ADAPTIVE_KIMI_AUTH_PROFILE=moonshot:api-key
ADAPTIVE_DISABLED_MODELS=moonshot/kimi-k3,openai/gpt-5.6-sol
```

Do not expose the contents of secret-bearing environment files in logs or chat.

### 6. Restart the OpenClaw gateway

```bash
openclaw gateway restart
```

This ensures the runtime observes current auth/config state.

### 7. Validate the Adaptive policy independently

Example:

```bash
cd "/home/ariel/Área de trabalho/VSCode/Git/adaptive-ai-orchestrator"

set -a
source "$HOME/.config/adaptive-ai-orchestrator/secrets.env"
set +a

python - <<'PY'
from application.model_routing_policy import ModelRoutingPolicy

p = ModelRoutingPolicy.from_env()

print("KIMI_ENABLED:", p.kimi_enabled)
print("HIGH_COMPLEXITY:", p.code_specialist_model)
print("ECONOMY:", p.economy_model)
print("ROUTINE_THINKING:", p.routine_thinking)
print("OAUTH_CONFIGURED:", bool(p.economy_auth_profile))
print("DISABLED:", p.disabled_models)
PY
```

This proves the **worker policy**, not the owner-session account.

### 8. Treat an existing owner-session auth pin as separate state

If an earlier owner session used the wrong OpenAI profile, do not assume changing
provider auth order retroactively replaces the session pin.

Prefer a fresh owner session after correcting auth order unless continuity
requirements justify explicit session-level repair.

### 9. Configure the owner session deliberately

For the current economy mode:

```text
model: GPT-5.6 Luna
reasoning: Low
fast mode: Off
account: intended ChatGPT OAuth profile
```

### 10. Run a minimal smoke test before the project prompt

Example:

```text
Responda apenas OAUTH_OK. Não use ferramentas e não altere nenhum arquivo.
```

A successful response proves basic execution but does not yet prove which
credential was used.

### 11. Verify the active model and auth

Run:

```text
/model status
```

Confirm all three:

```text
model: openai/gpt-5.6-luna
auth profile: intended OpenAI OAuth profile
auth type: OAuth
```

Only after this verification should a large handoff/project prompt be sent.

## Completion definition for a policy change

A policy migration is complete only when all of the following are true:

```text
[ ] code merged
[ ] local repository updated
[ ] provider profiles inspected
[ ] owner-agent auth order set
[ ] auth order verified
[ ] environment policy applied
[ ] gateway restarted
[ ] Adaptive worker policy validated
[ ] owner session model/reasoning selected
[ ] smoke test passed
[ ] /model status confirms intended auth
[ ] project workload starts only after verification
```

## Why the first activation attempt failed

The first activation sequence correctly changed:

- Adaptive routing code;
- `ADAPTIVE_OPENAI_OAUTH_PROFILE`;
- Kimi enable/disable policy;
- disabled premium models;
- gateway state.

However, it omitted:

```text
openclaw models auth order set --provider openai --agent sgfp <oauth-profile>
```

The manually-created owner session therefore used OpenClaw's normal account
selection and selected an OpenAI API-key profile. Because that API-key billing
account had no credits, the Luna turn failed even though the intended OAuth
subscription still had usage available.

The corrective sequence was:

```text
auth list
-> auth order set
-> auth order get
-> new owner session
-> Luna / Low
-> OAUTH_OK
-> /model status
-> OAuth confirmed
```

## Kimi balance transitions

When Kimi has no usable balance:

```text
ADAPTIVE_KIMI_ENABLED=0
```

High-complexity automatic work routes directly to Luna OAuth Low.

When usable balance returns:

```text
ADAPTIVE_KIMI_ENABLED=1
```

High-complexity work may use K2.7 again, with Luna OAuth Low as operational
fallback.

Changing this switch does not require removing K3 or Sol from the model catalog;
they remain manual-only premium options.

## Safety rules

- Never paste raw API keys or OAuth tokens into prompts.
- Prefer profile IDs in commands and diagnostics.
- Never assume model selection implies the intended billing product.
- Never declare an auth migration complete from a successful model response
  alone; verify `/model status`.
- Do not send a large project prompt before the smoke test and auth verification.
- Keep owner-session activation and worker-policy activation as separate checks.
