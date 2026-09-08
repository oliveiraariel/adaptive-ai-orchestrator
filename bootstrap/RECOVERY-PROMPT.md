# Recovery prompt — Adaptive + OpenClaw environment

Use this prompt with an AI assistant only when the automated bootstrap or verifier reports a problem.

```text
I need to recover my Adaptive AI Orchestrator + Ariel Agent Skills + OpenClaw environment on a Linux machine.

Canonical source:
- repository: oliveiraariel/adaptive-ai-orchestrator
- bootstrap contract: bootstrap/manifest.json
- bootstrap instructions: bootstrap/README.md
- troubleshooting: bootstrap/TROUBLESHOOTING.md
- setup: bootstrap/setup.sh
- verification: bootstrap/verify.sh
- updater: bootstrap/update.sh

Do not reconstruct the environment from memory or invent commands.

Procedure:
1. Read bootstrap/manifest.json, bootstrap/README.md and bootstrap/TROUBLESHOOTING.md first.
2. Inspect the current machine read-only before modifying anything.
3. Run or inspect `bootstrap/verify.sh` and use its first failing boundary as the diagnostic boundary.
4. Before reinstalling anything, distinguish shell/PATH discovery failures from actual missing software. If an `adaptive-openclaw-*` command is not found, inspect `~/.local/bin/adaptive-openclaw-*` and `$PATH` first. If the launcher exists, repair/reload PATH; do not reinstall the stack.
5. A bootstrap subprocess cannot mutate the already-open parent shell PATH. Current bootstrap versions persist `~/.local/bin` in shell startup files; a new terminal should see it. For the existing shell only, `export PATH="$HOME/.local/bin:$PATH"` is the bounded fix.
6. Consult the currently installed OpenClaw CLI help and current official OpenClaw documentation before changing OpenClaw configuration.
7. Prefer the existing bootstrap scripts and OpenClaw-owned `config`, `gateway`, `update`, `skills`, `sessions`, and `doctor` commands over direct edits to ~/.openclaw/openclaw.json.
8. Do not treat NVM/System-Node service warnings as a runtime failure when `openclaw gateway status --require-rpc` passes. Do not run `openclaw gateway install --force` merely to silence a warning.
9. Do not treat `Capability: read-only` in a Gateway status probe as proof that Adaptive execution is unavailable; use the live E2E boundaries.
10. Preserve all existing Git work. Never use reset --hard, clean -fd, force push, destructive checkout, or automatic conflict resolution.
11. Never print, paste, log, commit, or request the contents of the Gateway token, provider API keys, OAuth refresh tokens, passwords, or other credentials.
12. The intended Gateway secret contract is a file-backed OpenClaw SecretRef. Do not replace it with plaintext config unless I explicitly authorize a temporary diagnostic exception.
13. Keep the architecture boundary intact:
    OpenClaw chat → adaptive-orchestrator-bridge → Adaptive CLI/core → OpenClaw Gateway → agents → Adaptive evaluation.
14. Preserve the bridge recursion guard.
15. For automated user-invocable bridge tests, prefer the generic OpenClaw entrypoint `/skill adaptive-orchestrator-bridge ...` instead of assuming a friendly-name direct slash command is registered on every surface/version.
16. If inbound E2E reports insufficient evidence after the OpenClaw session completed, do not immediately call it a runtime failure. Inspect the session history read-only. The semantic proof is: project COMPLETED + required observed parallelism + fan-in marker. Humanized `Max parallelism observed: 3` is equivalent to `max_parallelism_observed: 3`.
17. Use `bootstrap/lib/e2e_evidence.py` and the verifier's printed diagnostic session key before manual interpretation. Exact AI phrasing is not authoritative when equivalent semantic evidence exists.
18. After any repair, run the repository tests, skill registry validation, OpenClaw config validation, Gateway RPC probe, bridge visibility check, and `bootstrap/verify.sh --e2e`.
19. Do not declare the environment recovered until the semantic verifier reports PASS. If a legacy verifier produced a false negative but session history proves the full semantic contract, update the verifier first and rerun rather than weakening the runtime.
20. `adaptive-openclaw-update` already runs full verification/E2E by default. Do not redundantly rerun Verify after a successful Update unless a fresh independent verification is desired.

If a provider login or OAuth flow is required, stop at that point and tell me exactly which official interactive authentication step I must complete. Resume only after I confirm it is complete.
```
