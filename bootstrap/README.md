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
18. runs live outbound and inbound end-to-end smoke tests;
19. installs Setup / Update / Verify launchers in the Linux application menu and, when available, on the desktop.

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
bash bootstrap/verify.sh --e2e
```

Checks Git repositories, Python, Adaptive tests, the skills registry, OpenClaw config, Gateway RPC, SecretRef wiring, file permissions, bridge visibility, and both integration directions.

### Update everything

```bash
bash bootstrap/update.sh
```

The updater:

- refuses to overwrite dirty Git worktrees;
- uses fast-forward-only Git integration;
- reinstalls the Adaptive editable environment;
- validates both repositories;
- uses OpenClaw's supported `openclaw update --yes` path;
- does **not** auto-accept new OpenClaw capability requests;
- runs full verification afterward.

### Setup / repair again

```bash
bash bootstrap/setup.sh
```

The setup is designed to be rerunnable. Existing file-backed tokens, repositories, and environments are reused when safe.

## Desktop launchers

After setup, these commands are also installed in `~/.local/bin`:

```text
adaptive-openclaw-setup
adaptive-openclaw-update
adaptive-openclaw-verify
```

Linux application-menu launchers are created with matching names.

## Live E2E contract

Verification tests both directions:

```text
Adaptive CLI
  → OpenClaw Gateway
  → main agent
  → Adaptive evaluation
```

and:

```text
OpenClaw agent
  → adaptive-orchestrator-bridge
  → Adaptive CLI/core
  → OpenClaw Gateway
  → main agent
  → Adaptive evaluation
  → OpenClaw response
```

The bridge's recursion guard prevents the nested OpenClaw agent from invoking the bridge again.

## Dry run

Preview setup without changing the machine:

```bash
bash bootstrap/setup.sh --dry-run
```

Preview updates:

```bash
bash bootstrap/update.sh --dry-run
```

## Source of truth

`bootstrap/manifest.json` records the canonical repositories, minimum runtime versions, security model, and E2E markers.

If future OpenClaw releases change CLI/config contracts, update this bootstrap in Git and let CI validate its static shell/manifest contract before using it on a new machine.

For an AI-assisted recovery when automation fails, use `bootstrap/RECOVERY-PROMPT.md`.
