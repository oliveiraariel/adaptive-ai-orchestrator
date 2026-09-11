from __future__ import annotations

from domain.provider_incident import PreflightFinding, RuntimeSnapshot


class RuntimePreflight:
    """Read-only integrity checks before or during provider/model execution."""

    def evaluate(self, snapshot: RuntimeSnapshot) -> tuple[PreflightFinding, ...]:
        findings: list[PreflightFinding] = []
        normalized_model = snapshot.model.strip().casefold()
        normalized_provider = snapshot.provider.strip().casefold()

        profile = snapshot.credential_profile
        if profile is not None:
            if profile.provider.strip().casefold() != normalized_provider:
                findings.append(
                    PreflightFinding(
                        code="credential-provider-mismatch",
                        severity="error",
                        message=(
                            f"Credential provider {profile.provider!r} does not match "
                            f"selected provider {snapshot.provider!r}."
                        ),
                        recommended_action="select-a-credential-issued-for-the-selected-provider",
                    )
                )
            if not profile.allows_model(snapshot.model):
                findings.append(
                    PreflightFinding(
                        code="credential-route-mismatch",
                        severity="error",
                        message=(
                            f"Credential product {profile.product!r} is not compatible "
                            f"with model route {snapshot.model!r}."
                        ),
                        recommended_action="switch-to-a-compatible-provider-route-or-credential-product",
                    )
                )

            product = profile.product.strip().casefold()
            if (
                product in {"kimi-platform", "moonshot-platform", "kimi-api-platform"}
                and normalized_model.startswith("kimi/")
            ):
                findings.append(
                    PreflightFinding(
                        code="kimi-platform-vs-kimi-code-route",
                        severity="error",
                        message=(
                            "A Kimi Platform pay-as-you-go credential is being used "
                            "with a Kimi Code-style kimi/* route."
                        ),
                        recommended_action="use-moonshot/kimi-* for-platform-credits-or-use-a-kimi-code-membership-key",
                    )
                )
            if (
                product in {"kimi-code", "kimi-code-membership"}
                and normalized_model.startswith("moonshot/")
            ):
                findings.append(
                    PreflightFinding(
                        code="kimi-code-vs-platform-route",
                        severity="warning",
                        message=(
                            "A Kimi Code membership credential is paired with a "
                            "Moonshot Platform route; verify that billing/auth product "
                            "selection is intentional."
                        ),
                        recommended_action="verify-endpoint-family-and-billing-product-before-dispatch",
                    )
                )

        if (
            snapshot.core_version
            and snapshot.plugin_version
            and snapshot.core_version != snapshot.plugin_version
        ):
            findings.append(
                PreflightFinding(
                    code="openclaw-plugin-version-mismatch",
                    severity="warning",
                    message=(
                        f"OpenClaw core {snapshot.core_version} and provider plugin "
                        f"{snapshot.plugin_version} are not aligned."
                    ),
                    recommended_action="inspect-plugin-runtime-metadata-before-reinstalling-or-updating",
                )
            )

        plugin_models = {item.strip().casefold() for item in snapshot.plugin_models}
        effective_models = {
            item.strip().casefold()
            for item in snapshot.effective_catalog_models
        }
        authored_models = {
            item.strip().casefold()
            for item in snapshot.authored_provider_models
        }
        if (
            normalized_model in plugin_models
            and normalized_model not in effective_models
            and authored_models
            and normalized_model not in authored_models
        ):
            findings.append(
                PreflightFinding(
                    code="provider-catalog-shadowing",
                    severity="error",
                    message=(
                        f"{snapshot.model!r} exists in the provider plugin but is "
                        "missing from the effective catalog while an authored provider "
                        "model list is present."
                    ),
                    recommended_action="remove-or-complete-the-authored-provider-model-list-then-refresh-catalog",
                )
            )

        native = snapshot.native_context_tokens
        effective = snapshot.effective_context_tokens
        if (
            isinstance(native, int)
            and native > 0
            and isinstance(effective, int)
            and effective > 0
            and effective < native
            and effective <= int(native * 0.5)
        ):
            findings.append(
                PreflightFinding(
                    code="context-window-mismatch",
                    severity="warning",
                    message=(
                        f"Selected model advertises {native} context tokens but the "
                        f"active session is using only {effective}."
                    ),
                    recommended_action="inspect-session-context-metadata-contextTokens-caps-and-live-switch-state",
                )
            )

        return tuple(findings)

    def blocking_findings(
        self,
        snapshot: RuntimeSnapshot,
    ) -> tuple[PreflightFinding, ...]:
        return tuple(
            finding
            for finding in self.evaluate(snapshot)
            if finding.blocks_execution
        )
