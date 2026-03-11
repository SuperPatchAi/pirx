#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv-docs/bin/python"
SCRIPT="${ROOT_DIR}/docs/build_science_pdf.py"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Error: missing docs venv python at ${PYTHON_BIN}"
  echo "Run:"
  echo "  python3 -m venv .venv-docs"
  echo "  .venv-docs/bin/python -m pip install reportlab"
  exit 1
fi

"${PYTHON_BIN}" "${SCRIPT}"
