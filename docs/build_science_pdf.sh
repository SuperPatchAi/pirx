#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="${ROOT_DIR}/docs"
MD_FILE="${DOCS_DIR}/The_Science_Behind_PIRX.md"
PDF_FILE="${DOCS_DIR}/The_Science_Behind_PIRX.pdf"
CSS_FILE="${DOCS_DIR}/science-paper.css"
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML_FILE="$(mktemp /tmp/pirx-science-XXXXXX.html)"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "Error: pandoc is required but not installed."
  exit 1
fi

if [[ ! -x "${CHROME_BIN}" ]]; then
  echo "Error: Google Chrome is required at:"
  echo "  ${CHROME_BIN}"
  exit 1
fi

cleanup() {
  rm -f "${HTML_FILE}"
}
trap cleanup EXIT

echo "Building HTML from markdown..."
pandoc "${MD_FILE}" \
  --standalone \
  --from markdown \
  --to html5 \
  --css "${CSS_FILE}" \
  --metadata title="The Science Behind PIRX" \
  -o "${HTML_FILE}"

echo "Printing PDF via headless Chrome..."
"${CHROME_BIN}" \
  --headless=new \
  --disable-gpu \
  --allow-file-access-from-files \
  --print-to-pdf-no-header \
  --print-to-pdf="${PDF_FILE}" \
  "file://${HTML_FILE}"

echo "Done: ${PDF_FILE}"
