# Recovery prompt — Adaptive + OpenClaw environment

Use this prompt with an AI assistant only when the automated bootstrap or verifier reports a problem.

```text
I need to recover my Adaptive AI Orchestrator + Ariel Agent Skills + OpenClaw environment on a Linux machine.

Canonical source:
- repository: oliveiraariel/adaptive-ai-orchestrator
- bootstrap contract: bootstrap/manifest.json
- bootstrap instructions: bootstrap/README.md
- setup: bootstrap/setup.sh
- verification: bootstrap/verify.sh
- updater: bootstrap/update.sh

Do not reconstruct the environment from memory or invent commands.

Procedure:
1. Read bootstrap/manifest.json and bootstrap/README.md first.
2. Inspect the current machine read-only before modifying anything.
3. Run or inspect `bootstrap/verify.sh` and use its failing checks as the diagnostic boundary.
4. Consult the currently installed OpenClaw CLI help and current official OpenClaw documentation before changing OpenClaw configuration.
5. Prefer the existing bootstrap scripts and OpenClaw-owned `config`, `gateway`, `update`, `skills`, and `doctor` commands over direct edits to ~/.openclaw/openclaw.json.
6. Preserve all existing Git work. Never use reset --hard, clean -fd, force push, destructive checkout, or automatic conflict resolution.
7. Never print, paste, log, commit, or request the contents of the Gateway token, provider API keys, OAuth refresh tokens, passwords, or other credentials.
8. The intended Gateway secret contract is a file-backed OpenClaw SecretRef. Do not replace it with plaintext config unless I explicitly authorize a temporary diagnostic exception.
9. Keep the architecture boundary intact:
   OpenClaw chat → adaptive-orchestrator-bridge → Adaptive CLI/core → OpenClaw Gateway → agents → Adaptive evaluation.
10. Preserve the bridge recursion guard.
11. After any repair, run the repository tests, skill registry validation, OpenClaw config validation, Gateway RPC probe, bridge visibility check, and `bootstrap/verify.sh --e2e`.
12. Do not declare the environment recovered until the verifier reports PASS.

If a provider login or OAuth flow is required, stop at that point and tell me exactly which official interactive authentication step I must complete. Resume only after I confirm it is complete.
```
