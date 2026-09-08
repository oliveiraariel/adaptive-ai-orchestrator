# Adaptive + OpenClaw Reproducible Bootstrap

This directory turns the Adaptive AI Orchestrator + Ariel Agent Skills + OpenClaw integration into a reproducible Linux environment instead of a sequence of manual terminal steps.

## New computer: one command

On Linux Mint / Ubuntu / Debian-family systems:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh | bash
```

The installer clones the two canonical repositories under:

```text
~/Projects/AdaptiveOpenClaw/
├── adaptive-ai-orchestrator/
└── ariel-agent-skills/
```

Override the parent directory when needed:

```bash
curl -fsSL https://raw.githubusercontent.com/oliveiraariel/adaptive-ai-orchestrator/main/install.sh \
  | bash -s -- --stack-root "$HOME/MeuDiretorio"
```

## What is automated

The bootstrap:

1. verifies a Debian/Ubuntu/Linux Mint host;
2. installs basic system prerequisites when missing;
3. requires Python 3.12+;
4. safely clones/fast-forwards the Adaptive and Skills repositories;
5. creates the Adaptive `.venv`;
6. installs `.[test,gateway]`;
7. runs the Adaptive test suite;
8. validates the Ariel Agent Skills registry;
9. installs OpenClaw through the official stable installer when absent;
10. launches OpenClaw onboarding only when the local configuration is not ready;
11. adds `ariel-agent-skills` to `skills.load.extraDirs` without deleting existing roots;
12. reuses an existing file-backed Gateway token, migrates an existing `OPENCLAW_GATEWAY_TOKEN` from the shell or systemd user environment when present, or generates a cryptographically random token when neither exists;
13. stores that token in a mode-`0600` file;
14. configures OpenClaw `SecretRef` objects so the Gateway and `adaptive-orchestrator-bridge` share that secret without writing it into prompts or command arguments;
15. validates the OpenClaw config;
16. restarts or installs the managed Gateway service, then removes the legacy systemd user token environment after the SecretRef migration succeeds;
17. validates Gateway RPC, `main`, the bridge skill, and the skills catalog;
18. installs Setup / Update / Verify command launchers before the live E2E, persists `~/.local/bin` in the user's shell startup PATH, and installs application-menu/desktop launchers when available;
19. runs live outbound, direct multiagent, and inbound bridge end-to-end tests;
20. validates inbound E2E semantically from the direct CLI result plus OpenClaw session history so harmless AI wording changes do not create false negatives.

Installing recovery launchers **before** the final live E2E is intentional: even if a provider/runtime problem blocks the last gate, the machine already has a stable Setup / Update / Verify recovery path.

## The only unavoidable interactive step

A fresh computer still needs **your model-provider authentication**. When OpenClaw has no valid configuration, the bootstrap launches:

```bash
openclaw onboard --install-daemon
```

Complete the OpenClaw wizard (for example, authenticate OpenAI). The bootstrap resumes automatically afterward.

The installer does not attempt to copy OAuth refresh tokens, API keys, passwords, or other provider credentials from GitHub.

## Security model

The bootstrap standardizes local Gateway authentication on token mode.

The shared token is stored at:

```text
~/.openclaw/secrets/adaptive-gateway-token.txt
```

with file mode `0600`.

OpenClaw is configured with a file SecretRef provider named:

```text
adaptive_gateway_file
```

Both of these surfaces reference the same secret:

```text
gateway.auth.token
skills.entries.adaptive-orchestrator-bridge.apiKey
```

The bridge declares `OPENCLAW_GATEWAY_TOKEN` as its primary environment variable, so OpenClaw resolves the SecretRef and injects the token only for the skill execution. The token is not committed to either repository.

A machine previously configured with `systemctl --user set-environment OPENCLAW_GATEWAY_TOKEN=...` is migrated without rotating the token: the value is copied directly into the protected SecretRef file without being printed, the Gateway is restarted successfully, and only then is the legacy systemd user environment variable cleared.

If the Control UI explicitly asks for the token, reveal it locally with:

```bash
bash bootstrap/show-dashboard-token.sh
```

Do not paste that value into ChatGPT, GitHub issues, screenshots, or documentation.

## Daily operations

### Verify everything

```bash
adaptive-openclaw-verify
```

Script fallback:

```bash
bash bootstrap/verify.sh --e2e
```

Checks Git repositories, Python, Adaptive tests, the skills registry, OpenClaw config, Gateway RPC, SecretRef wiring, file permissions, bridge visibility, and all three integration paths.

### Update everything

```bash
adaptive-openclaw-update
```

Script fallback:

```bash
bash bootstrap/update.sh
```

The updater:

- refuses to overwrite dirty Git worktrees;
- uses fast-forward-only Git integration;
- refreshes the `adaptive-openclaw-*` launchers from the newly synchronized repository;
- reapplies the persistent `~/.local/bin` shell PATH registration idempotently;
- reinstalls the Adaptive editable environment;
- validates both repositories;
- uses OpenClaw's supported `openclaw update --yes` path unless `--skip-openclaw` is requested;
- does **not** auto-accept new OpenClaw capability requests;
- runs full verification/E2E afterward by default.

A successful `adaptive-openclaw-update` therefore does **not** need an immediate second Verify run. Use Verify separately when you want a fresh check without updating, or after a targeted repair.

#### One-time transition from a pre-self-heal updater

A running shell process keeps executing the script version that was loaded when that command started. If an older updater fast-forwards the repository and downloads a newer updater containing launcher/PATH self-heal logic, that already-running old process cannot retroactively execute the new lines.

For that one migration only, after the repository has been updated, refresh the recovery surface explicitly:

```bash
bash "$HOME/Área de trabalho/VSCode/Git/adaptive-ai-orchestrator/bootstrap/install-launchers.sh" \
  --stack-root "$HOME/Área de trabalho/VSCode/Git"
```

Use the actual repository/stack path on machines installed elsewhere.

After this transition, future `adaptive-openclaw-update` runs perform launcher/PATH self-healing automatically; this is **not** a recurring manual step.

### Setup / repair again

```bash
adaptive-openclaw-setup
```

Script fallback:

```bash
bash bootstrap/setup.sh
```

The setup is designed to be rerunnable. Existing file-backed tokens, repositories, and environments are reused when safe.

## Terminal launcher PATH contract

The command launchers are installed in:

```text
~/.local/bin
```

Current bootstrap versions idempotently add that directory to `~/.profile` and to the active shell's common startup file (`~/.bashrc` for Bash or `~/.zshrc` for Zsh).

A child installer process cannot modify the environment of a terminal that was already open before setup. Therefore, immediately after a first install, if the **same old terminal** still reports `command not found`, either open a new terminal or run once in that shell:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Before reinstalling anything, verify whether the launchers already exist:

```bash
ls -l ~/.local/bin/adaptive-openclaw-*
```

If they exist, the problem is shell discovery/PATH, not a missing Adaptive/OpenClaw installation.

## Desktop launchers

These commands are installed in `~/.local/bin`:

```text
adaptive-openclaw-setup
adaptive-openclaw-update
adaptive-openclaw-verify
```

Linux application-menu launchers are created with matching names.

## Live E2E contract

Verification has three explicit gates.

### E2E 1 — bounded outbound

```text
Adaptive CLI
  → OpenClaw Gateway
  → main agent
  → Adaptive evaluation
```

### E2E 2 — real scalable multiagent execution

```text
Adaptive project mode
  → 3 parallel OpenClaw worker sessions
  → accepted worker results
  → fan-in
  → Adaptive
```

The test requires `max_parallelism_observed >= 3` and the fan-in marker.

### E2E 3 — inbound bridge path

```text
OpenClaw agent
  → /skill adaptive-orchestrator-bridge
  → Adaptive CLI/core project mode
  → OpenClaw Gateway workers
  → parallel execution
  → fan-in
  → OpenClaw response
```

The bridge's recursion guard prevents nested worker recursion.

The E2E 3 verifier does **not** require one exact AI sentence. It validates semantic evidence from both the direct OpenClaw CLI result and `chat.history` using `bootstrap/lib/e2e_evidence.py`:

```text
project status = COMPLETED
max parallelism observed >= 3
fan-in marker = ADAPTIVE_MULTIAGENT_FANIN_OK
```

Thus `Max parallelism observed: 3` and `max_parallelism_observed: 3` are equivalent evidence.

If semantic validation fails, the verifier prints the diagnostic session key so history can be inspected read-only without repeating the expensive E2E immediately.

## Operational warnings versus real failures

Do not confuse service-maintenance warnings with an execution failure. In particular, a Gateway warning about Node being supplied through NVM/version managers does not invalidate a running Gateway when:

```text
Runtime: running
Read probe: ok
Listening: 127.0.0.1:<port>
```

and `openclaw gateway status --require-rpc` succeeds.

Similarly, `Capability: read-only` on a status probe is not by itself evidence that Adaptive worker execution is unavailable. The live E2E is the execution proof.

Do not run `openclaw gateway install --force` merely to silence those warnings. Handle System Node/service migration as a separate maintenance task.

## Dry run

Preview setup without changing the machine:

```bash
bash bootstrap/setup.sh --dry-run
```

Preview updates:

```bash
bash bootstrap/update.sh --dry-run
```

## Troubleshooting and recovery

Read [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) before manual repair. It records the failure classification order, PATH diagnosis, the one-time legacy-updater transition, Gateway warning interpretation, inbound E2E semantic fallback, and read-only session-history diagnostic.

For an AI-assisted recovery, use [`RECOVERY-PROMPT.md`](RECOVERY-PROMPT.md). The recovery prompt explicitly instructs the assistant to diagnose the first failing boundary rather than reinstalling working layers.

## Source of truth

`bootstrap/manifest.json` records the canonical repositories, minimum runtime versions, security model, launcher/PATH contract, and E2E validation contract.

If future OpenClaw releases change CLI/config contracts, update this bootstrap in Git and let CI validate its static shell/manifest contract before using it on a new machine.
