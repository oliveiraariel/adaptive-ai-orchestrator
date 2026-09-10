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

echo "Adaptive AI Orchestrator pronto."
echo "Ambiente virtual: ativo"
echo "OpenClaw Gateway token: carregado"

unset PROJECT_ROOT TOKEN_FILE
