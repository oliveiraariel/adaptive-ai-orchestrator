# Mandatory Release Artifact Governance v1

## Status

This policy is a cross-project Adaptive AI Orchestrator rule for work that **creates or regenerates an installable/deployable release artifact** such as a ZIP, plugin/theme package, runtime bundle, or equivalent archive.

Runtime marker:

```text
ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1
```

The policy is intentionally independent of programming language, framework, archive format, package manager, hosting platform, and deployment target.

## Why runtime enforcement exists

A packaging checklist written only in a human prompt is insufficient. Packaging work can originate from API, backend, frontend, debugging, hotfix, or retest flows, and workers can be delegated without the operator repeating a long release recipe.

The adopted design therefore has two layers:

1. **Runtime enforcement** at the common `TaskPackage` boundary. Packaging work receives the mandatory policy automatically.
2. **Human-readable shorthand** in `docs/prompts/GERAR-PACOTE-RETESTE.md` for operators who want a concise explicit entry point.

Project-specific release conventions remain authoritative. This policy supplies minimum artifact-integrity obligations and never replaces canonical project facts.

## Activation scope

The policy applies when the delegated objective/scope/context indicates creation or regeneration of a release artifact, including examples such as:

- generate a fresh ZIP for retest;
- package a WordPress plugin or theme;
- build an installable package;
- create a release archive/runtime bundle;
- regenerate an artifact after a hotfix;
- create a deployment package without actually deploying it.

The policy does **not** automatically activate for merely inspecting, hashing, downloading, installing, or activating an existing artifact. Those operations have different authority and safety concerns.

The marker `ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1` can be supplied explicitly when packaging intent is known but not obvious from the Work Unit wording.

## Mandatory cross-stack invariants

### 1. Exact source identity

Before packaging, identify the authoritative repository/worktree and the intended source state:

- branch/ref where applicable;
- HEAD/commit where available;
- working-tree state;
- whether intentional uncommitted WIP is part of the artifact.

Package the intended current state, not a stale commit or a previously generated archive. Dirty WIP is not automatically invalid, but it must be explicit and traceable.

### 2. Validation belongs to the packaged state

Run the smallest sufficient **existing project-defined** validation set relevant to the artifact. Depending on the project this can include build, tests, lint/syntax, contract/composition checks, or smoke tests.

Do not globally invent Composer, npm, PHPUnit, WordPress, Docker, or other stack-specific commands. Use the project's actual gates.

A validation may be reported as `PASS` only when it was actually executed against the source state being packaged. A required local gate that fails prevents the artifact from being described as ready, unless the artifact is explicitly diagnostic and marked not-ready.

### 3. Fresh artifact after a change or retest request

When the purpose is a fix, hotfix, regression retest, or environmental retest, create a **new artifact after the validated change**.

Do not silently reuse an older ZIP/archive and do not ambiguously overwrite an old artifact when doing so would break traceability.

### 4. Naming and identity

Project-specific naming rules take precedence. When none exists, use a unique descriptive artifact name containing the artifact/purpose and a date-time discriminator appropriate to the environment.

Example only:

```text
<artifact>-<purpose>-YYYYMMDD-HHMM.zip
```

The filename is convenience, not proof of identity. Source identity plus SHA-256 is the authoritative artifact fingerprint.

### 5. Runtime-only composition

Include only material required by the target runtime, including production dependencies/autoload/assets when applicable.

Exclude unless explicitly required at runtime:

- `.git` and source-control metadata;
- `.env`, credentials, secrets, tokens, private keys;
- tests and test fixtures;
- caches and temporary files;
- local runtime state;
- development-only tooling;
- development-only documentation.

### 6. Installable structure

Validate the structure required by the actual target platform:

- correct package root;
- required entrypoint/manifests;
- production autoload/dependencies;
- runtime assets;
- no accidental extra nesting.

This is platform-aware, not WordPress-specific. Do not impose a plugin layout on a service bundle or vice versa.

### 7. Integrity and sensitive-file checks

Before declaring the artifact ready:

- run the archive/package integrity check appropriate to the format (`unzip -t` or equivalent where applicable);
- verify required runtime files exist;
- verify forbidden sensitive/development files are absent;
- compute SHA-256;
- record artifact size.

### 8. Required packaging evidence

The result must report, when applicable:

- source branch/ref;
- source HEAD/commit;
- working-tree state;
- validations actually executed and their outcomes;
- artifact filename and path;
- package root;
- main runtime entrypoint/manifest;
- size;
- SHA-256;
- integrity-check result;
- `Ready for environmental retest: YES/NO`.

Do not infer evidence that was not collected.

### 9. Packaging is not deployment authority

Creating an artifact does not authorize:

- merge;
- publish/release to a registry;
- upload to production;
- remote installation;
- activation;
- deployment;
- destructive environment mutations.

Those remain separate authority checkpoints.

### 10. Local readiness is not environmental validation

A valid package can be ready for environmental retest while the real runtime validation remains pending.

Always distinguish package/local evidence from installation, activation, database, network, browser, hosting-platform, or production evidence.

## Interaction with API governance

`ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1` is separate from `ADAPTIVE_API_GENERATION_POLICY_V1`.

A Work Unit can receive both policies. For example, packaging a plugin that exposes a REST API can require API-contract governance **and** release-artifact governance. Packaging a non-API theme/package receives only the artifact policy.

This separation avoids turning API governance into a framework-specific ZIP recipe.

## Precedence

```text
approved project facts / explicit human authority
        ↓
project-specific release/build/package conventions
        ↓
ADAPTIVE_RELEASE_ARTIFACT_POLICY_V1 minimum obligations
        ↓
format/platform-specific implementation choices
```

A project may be stricter. The global policy must not silently weaken its gates.

## Implementation boundary

Mandatory enforcement lives in `src/domain/release_artifact_policy.py` and is applied by `TaskPackage` before delegated execution. The prompt template is convenience, not the enforcement boundary.

The detector intentionally requires a packaging action plus an artifact signal so ordinary inspection or installation of an existing ZIP does not become artifact-generation work.
