#!/usr/bin/env bash
# After a successful Eudic→Anki import: clear only the external temp directory.
#
# Default temp dir: ~/Documents/eudic-to-anki-temp
# Optional override for testing/custom setups: EUDIC_TO_ANKI_TEMP_DIR=/path/to/temp
# Set KEEP_EUDIC_IMPORT_ARTIFACTS=1 to skip deletion.
set -euo pipefail

DEFAULT_TEMP_DIR="${HOME}/Documents/eudic-to-anki-temp"
TEMP_DIR="${EUDIC_TO_ANKI_TEMP_DIR:-${DEFAULT_TEMP_DIR}}"

echo "== cleanup_import_artifacts =="
echo "Temp dir: ${TEMP_DIR}"
mkdir -p "${TEMP_DIR}"

_clear_temp_dir_contents() {
  if [[ ! -d "${TEMP_DIR}" ]]; then
    return 0
  fi
  shopt -s nullglob dotglob
  local path base
  for path in "${TEMP_DIR}/"* "${TEMP_DIR}/".[!.]* "${TEMP_DIR}/"..?*; do
    [[ ! -e "${path}" ]] && continue
    base="$(basename "${path}")"
    [[ "${base}" == "." || "${base}" == ".." ]] && continue
    rm -rf "${path}"
  done
  shopt -u nullglob dotglob
}

if [[ -n "${KEEP_EUDIC_IMPORT_ARTIFACTS:-}" ]]; then
  echo "Skipped clearing temp dir (KEEP_EUDIC_IMPORT_ARTIFACTS=1)."
else
  _clear_temp_dir_contents
  echo "Done. Cleared ${TEMP_DIR}."
fi
