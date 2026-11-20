#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d .venv ]; then ./scripts/setup_playground.sh; fi
./scripts/preflight_demo.sh

export PRUNIN_ENABLE_OLLAMA="${PRUNIN_ENABLE_OLLAMA:-1}"
export PRUNIN_OLLAMA_MODEL="${PRUNIN_OLLAMA_MODEL:-qwen3:8b}"
if [ "$PRUNIN_ENABLE_OLLAMA" = "1" ]; then
  if command -v ollama >/dev/null 2>&1; then
    if ! curl -fs http://localhost:11434/api/tags >/dev/null 2>&1; then
      echo "Iniciando Ollama..."
      (ollama serve >/tmp/prunin_ollama.log 2>&1 &)
      for _ in $(seq 1 30); do
        curl -fs http://localhost:11434/api/tags >/dev/null 2>&1 && break
        sleep 1
      done
    fi
    if ! ollama list 2>/dev/null | grep -q "^${PRUNIN_OLLAMA_MODEL}"; then
      echo "Modelo ${PRUNIN_OLLAMA_MODEL} no instalado; se usará el respaldo determinístico." >&2
      echo "Instálalo manualmente si se necesita: ollama pull ${PRUNIN_OLLAMA_MODEL}" >&2
    fi
    # Precarga el modelo para la primera consulta
    curl -fs http://localhost:11434/api/generate -d "{\"model\":\"${PRUNIN_OLLAMA_MODEL}\",\"keep_alive\":\"30m\"}" >/dev/null 2>&1 || true
  else
    echo "Ollama no está instalado; se usará el respaldo determinístico." >&2
    export PRUNIN_ENABLE_OLLAMA=0
  fi
fi
printf '\nAbriendo PRUNIN AI Core en http://localhost:8000\n'
(sleep 2; open http://localhost:8000 >/dev/null 2>&1 || true) &
./scripts/run_playground.sh
