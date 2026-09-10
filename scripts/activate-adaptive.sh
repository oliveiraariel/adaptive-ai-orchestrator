#!/usr/bin/env bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOKEN_FILE="$HOME/.openclaw/secrets/adaptive-gateway-token.txt"

if [[ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
    echo "Erro: ambiente virtual do Adaptive não encontrado."
    return 1
fi

if [[ ! -f "$TOKEN_FILE" ]]; then
    echo "Erro: token do OpenClaw Gateway não encontrado."
    return 1
fi

source "$PROJECT_ROOT/.venv/bin/activate"
export OPENCLAW_GATEWAY_TOKEN="$(< "$TOKEN_FILE")"
# Completed/cancelled Adaptive worker sessions are archived only after their
# result/abort boundary is safely observed. Set 0 before sourcing to disable
# this temporarily while diagnosing session lifecycle behavior.
export ADAPTIVE_SESSION_AUTO_ARCHIVE="${ADAPTIVE_SESSION_AUTO_ARCHIVE:-1}"

echo "Adaptive AI Orchestrator pronto."
echo "Ambiente virtual: ativo"
echo "OpenClaw Gateway token: carregado"
echo "Auto-arquivamento de sessões: $ADAPTIVE_SESSION_AUTO_ARCHIVE"

unset PROJECT_ROOT TOKEN_FILE
