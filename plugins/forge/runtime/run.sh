#!/usr/bin/env bash
# Wrapper for forge server — serves $FORGE_DIR (default: ~/.roxabi/forge) on port 8080.
if [ -n "${DIAGRAMS_DIR:-}" ] && [ -z "${FORGE_DIR:-}" ]; then
  echo "⚠ DIAGRAMS_DIR is deprecated — use FORGE_DIR" >&2
fi
export FORGE_DIR="${FORGE_DIR:-${DIAGRAMS_DIR:-$HOME/.roxabi/forge}}"

exec python3 "$FORGE_DIR/serve.py"