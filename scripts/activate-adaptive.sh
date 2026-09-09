#!/usr/bin/env bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

if [[ ! -f ".venv/bin/activate" ]]; then
    echo "Erro: ambiente virtual .venv não encontrado."
    return 1
fi

if [[ ! -f "$HOME/.openclaw/secrets/adaptive-gateway-token.txt" ]]; then
    echo "Erro: token do OpenClaw Gateway não encontrado."
    return 1
fi

source .venv/bin/activate
export OPENCLAW_GATEWAY_TOKEN="$(< "$HOME/.openclaw/secrets/adaptive-gateway-token.txt")"

echo "Adaptive AI Orchestrator pronto."
echo "Ambiente virtual: ativo"
echo "OpenClaw Gateway token: carregado"
