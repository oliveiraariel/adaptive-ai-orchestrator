# Adaptive + OpenClaw Bootstrap Troubleshooting

This document records failure modes that must be diagnosed before reinstalling or rewriting configuration. It exists so a future setup/recovery does not repeat avoidable manual debugging.

## 1. Launcher exists but the command is not found

Symptom:

```text
adaptive-openclaw-update: command not found
```

First inspect, do not reinstall:

```bash
printf 'PATH=%s\n' "$PATH"
ls -l ~/.local/bin/adaptive-openclaw-* 2>/dev/null || true
```

The launchers live in `~/.local/bin`. Current bootstrap versions register that directory idempotently in shell startup files. A bootstrap subprocess cannot modify the PATH of a parent terminal that was already open before setup.

For the same already-open shell only:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Opening a new terminal should load the persisted PATH entry.

Do **not** reinstall Adaptive, Skills, or OpenClaw merely because the shell cannot resolve a launcher whose file already exists.

### 1.1 One-time transition from an older updater

An updater process reads and executes the script version that existed when that process started. If an older `adaptive-openclaw-update` fast-forwards the repository and downloads a newer updater that contains launcher/PATH self-healing, the already-running old Bash process cannot retroactively begin executing the newly downloaded code.

Therefore, when migrating from a pre-self-heal bootstrap, one explicit launcher refresh may be required **once after the repository has been updated**:

```bash
bash "$HOME/Área de trabalho/VSCode/Git/adaptive-ai-orchestrator/bootstrap/install-launchers.sh" \
  --stack-root "$HOME/Área de trabalho/VSCode/Git"
```

Use the actual stack root if the repositories are installed elsewhere.

After that transition, current `adaptive-openclaw-update` refreshes the launchers and persisted `~/.local/bin` PATH registration automatically on future updates. This is a migration characteristic, not a recurring manual maintenance step.

## 2. Gateway status shows NVM / service warnings

Warnings about a Gateway service using Node through NVM/version managers are maintenance warnings unless an actual runtime probe fails.

Use the operational boundary:

```bash
openclaw gateway status --require-rpc
```

If the service is running, the read probe is OK, and the Gateway is listening, do not run `openclaw gateway install --force` merely to silence the warning. Treat service migration to a supported System Node as a separate maintenance task.

## 3. `Capability: read-only` in Gateway status

A read-only status capability describes the diagnostic caller/probe boundary. It is not by itself evidence that Adaptive workers or the bridge cannot execute.

Use the live E2E tests as the execution proof instead of inferring failure from that status line.

## 4. Inbound E2E appears to fail after the OpenClaw session finished

Do not assume the bridge or Adaptive failed merely because the verifier did not find one exact output spelling.

The inbound contract is semantic:

- project status is `COMPLETED`;
- observed parallelism is at least the required minimum (currently `3` in bootstrap E2E);
- `ADAPTIVE_MULTIAGENT_FANIN_OK` is present.

Humanized output such as:

```text
Max parallelism observed: 3
```

is equivalent evidence to:

```text
max_parallelism_observed: 3
```

The verifier now reads both the direct CLI result and the completed OpenClaw `chat.history`, then validates semantic evidence with `bootstrap/lib/e2e_evidence.py`.

If semantic validation still fails, the verifier prints the diagnostic session key. Inspect it read-only:

```bash
openclaw gateway call chat.history \
  --params '{"sessionKey":"<printed-session-key>","limit":100,"maxChars":200000}' \
  --json
```

Never expose Gateway tokens or provider credentials while sharing diagnostics.

## 5. Skill invocation compatibility

For automated inbound verification, prefer the OpenClaw generic user-invocable skill entrypoint:

```text
/skill adaptive-orchestrator-bridge ...
```

This avoids depending on whether a particular OpenClaw surface/version registers the skill's friendly name as a direct slash command.

## 6. Update versus Verify

`adaptive-openclaw-update` already runs repository validation and full verification/E2E by default after updating.

Therefore the normal sequence is:

```text
adaptive-openclaw-update
→ if PASS, no second Verify is required
```

Run `adaptive-openclaw-verify` separately when you want a fresh verification without updating, or after a targeted repair.

## 7. Failure classification before repair

Classify a failure before changing anything:

```text
shell discovery / PATH
→ repository sync
→ Python/dependencies/tests
→ OpenClaw config
→ Gateway RPC
→ skill visibility
→ outbound Adaptive E2E
→ direct multiagent E2E
→ inbound bridge E2E
→ semantic evidence formatting
```

Repair the first failing boundary only. Do not replace a working lower layer because a higher-layer assertion failed.

## 8. Known validated E2E shape

A successful complete verification proves:

```text
E2E 1
Adaptive → OpenClaw → Adaptive

E2E 2
Adaptive → 3 parallel OpenClaw worker sessions → fan-in → Adaptive

E2E 3
OpenClaw → adaptive-orchestrator-bridge → Adaptive project mode
→ parallel workers → fan-in → OpenClaw
```

The test harness must distinguish **runtime failure** from **presentation-format variation**. Exact phrasing from an AI response is never the source of truth when equivalent structured/semantic evidence is available.
