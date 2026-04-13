#!/usr/bin/env bash
# After a successful Eudic→Anki import: clear the skill's import_scratch/ folder
# and remove legacy intermediate files that were previously written next to SKILL.md.
#
# Set KEEP_EUDIC_IMPORT_ARTIFACTS=1 to keep everything under import_scratch/ and to keep
# root-level _week_*_import.json / _week_*.csv (if any remain from older runs).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SKILLS_ROOT="$(dirname "$SKILL_DIR")"
# Repo root: .../skills/eudic-to-anki/scripts -> four levels up
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
SCRATCH="${SKILL_DIR}/import_scratch"

echo "== cleanup_import_artifacts: ${SKILL_DIR} =="
mkdir -p "${SCRATCH}"

_clear_scratch_contents() {
  if [[ ! -d "${SCRATCH}" ]]; then
    return 0
  fi
  shopt -s nullglob dotglob
  local path base
  for path in "${SCRATCH}/"* "${SCRATCH}/".[!.]* "${SCRATCH}/"..?*; do
    [[ ! -e "${path}" ]] && continue
    base="$(basename "${path}")"
    [[ "${base}" == "." || "${base}" == ".." ]] && continue
    [[ "${base}" == ".gitkeep" || "${base}" == ".gitignore" ]] && continue
    rm -rf "${path}"
  done
  shopt -u nullglob dotglob
}

# --- Legacy: intermediates once written in the skill root (not import_scratch/) ---
shopt -s nullglob
for f in \
  "${SKILL_DIR}/_week_partial.json" \
  "${SKILL_DIR}/_week_partial_words_only.json" \
  "${SKILL_DIR}/minimal_coach_week.json" \
  "${SKILL_DIR}/week_coach_by_word.json"
do
  [[ -e "$f" ]] && rm -fv "$f"
done
for f in "${SKILL_DIR}/"_dia_*.json; do
  [[ -e "$f" ]] && rm -fv "$f"
done
for f in "${SKILL_DIR}/"_day_*.csv "${SKILL_DIR}/"_recent_* "${SKILL_DIR}/"_last_week_*; do
  [[ -e "$f" ]] && rm -fv "$f"
done

for f in "${SKILL_DIR}/"_week_*.json; do
  [[ -e "$f" ]] || continue
  base="$(basename "$f")"
  if [[ "${base}" == *_import.json ]] && [[ -n "${KEEP_EUDIC_IMPORT_ARTIFACTS:-}" ]]; then
    continue
  fi
  rm -fv "$f"
done

if [[ -z "${KEEP_EUDIC_IMPORT_ARTIFACTS:-}" ]]; then
  for f in "${SKILL_DIR}/"_week_*_import.json "${SKILL_DIR}/"_week_*.csv; do
    [[ -e "$f" ]] && rm -fv "$f"
  done
  _clear_scratch_contents
else
  echo "Skipped clearing import_scratch/ (KEEP_EUDIC_IMPORT_ARTIFACTS=1)."
fi
shopt -u nullglob

# TTS temp files (ankiconnect default: cwd-relative generated_audio/)
if [[ -d "${REPO_ROOT}/generated_audio" ]]; then
  rm -fv "${REPO_ROOT}/generated_audio/"*.mp3 2>/dev/null || true
  rmdir "${REPO_ROOT}/generated_audio" 2>/dev/null || true
fi
if [[ -d "${SKILLS_ROOT}/generated_audio" ]]; then
  rm -fv "${SKILLS_ROOT}/generated_audio/"*.mp3 2>/dev/null || true
  rmdir "${SKILLS_ROOT}/generated_audio" 2>/dev/null || true
fi

if [[ -n "${KEEP_EUDIC_IMPORT_ARTIFACTS:-}" ]]; then
  echo "Done. Kept import_scratch/ and root _week_* CSV / *_import.json (KEEP_EUDIC_IMPORT_ARTIFACTS=1)."
else
  echo "Done. Cleared import_scratch/ (except .gitkeep/.gitignore), legacy root intermediates, and TTS cache where present."
fi
