#!/usr/bin/env bash
# One-shot checks for eudic-to-anki: repo layout, token, AnkiConnect, Edge-TTS.
# Run from anywhere; paths are resolved from this script's location.

set -u

failures=0
warnings=0

say_ok() { printf ' [OK] %s\n' "$1"; }
say_warn() { printf '  [WARN] %s\n' "$1"; warnings=$((warnings + 1)); }
say_fail() { printf '  [FAIL] %s\n' "$1"; failures=$((failures + 1)); }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

EUDIC_EXPORT="$SCRIPT_DIR/eudic_export.py"
ANKI_IMPORT="$SCRIPT_DIR/ankiconnect_import.py"
EDGE_TTS_RUNNER="$SCRIPT_DIR/edge_tts_runner.py"
RUN_LOGIN_ZSH="$SCRIPT_DIR/run_with_login_zsh.py"
VOCAB_MODEL="$SKILL_DIR/assets/trvs_lab_model.json"

echo "== eudic-to-anki / check_env =="
echo "Skill root: $SKILL_DIR"
echo

echo "== Python =="
if command -v python3 >/dev/null 2>&1; then
  say_ok "python3: $(python3 --version 2>&1)"
else
  say_fail "python3 not found in PATH"
fi
echo

echo "== Bundled scripts & assets =="
for path in "$EUDIC_EXPORT" "$ANKI_IMPORT" "$EDGE_TTS_RUNNER" "$RUN_LOGIN_ZSH"; do
  if [[ -f "$path" ]]; then
    say_ok "present: ${path#$SKILL_DIR/}"
  else
    say_fail "missing: ${path#$SKILL_DIR/}"
  fi
done
if [[ -f "$VOCAB_MODEL" ]]; then
  say_ok "TRVS-Lab model present: ${VOCAB_MODEL#$SKILL_DIR/}"
else
  say_fail "missing: ${VOCAB_MODEL#$SKILL_DIR/}"
fi
echo

echo "== Eudic API token =="
if [[ -n "${EUDIC_TOKEN:-}" ]]; then
  say_ok "EUDIC_TOKEN is set in this shell (value hidden)"
elif [[ -f "$RUN_LOGIN_ZSH" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 "$RUN_LOGIN_ZSH" python3 -c 'import os, sys; sys.exit(0 if os.environ.get("EUDIC_TOKEN") else 1)' 2>/dev/null; then
    say_ok "EUDIC_TOKEN is available under login zsh (not in this shell); prefix commands with: python3 ${RUN_LOGIN_ZSH#$SKILL_DIR/}"
  else
    say_warn "EUDIC_TOKEN not set here and not found under zsh -lic; export it or pass --token to eudic_export.py"
  fi
else
  say_warn "EUDIC_TOKEN is not set; export it or pass --token when running eudic_export.py"
fi
echo

echo "== AnkiConnect =="
if [[ -f "$ANKI_IMPORT" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 "$ANKI_IMPORT" --ping; then
    say_ok "AnkiConnect responded (see line above)"
  else
    say_fail "AnkiConnect ping failed; open Anki and confirm add-on on http://127.0.0.1:8765"
  fi
else
  say_fail "Cannot run AnkiConnect ping (missing python3 or ankiconnect_import.py)"
fi
echo

echo "== Edge-TTS (pronunciation audio) =="
if [[ -f "$EDGE_TTS_RUNNER" ]] && command -v python3 >/dev/null 2>&1; then
  if python3 -m py_compile "$EDGE_TTS_RUNNER" 2>/dev/null; then
    say_ok "edge_tts_runner.py parses (py_compile)"
  else
    say_warn "edge_tts_runner.py py_compile failed; check Python deps"
  fi
fi

if python3 -c "import edge_tts" 2>/dev/null; then
  say_ok "edge-tts Python package importable"
else
  say_warn "edge-tts not installed; run: pip install edge-tts"
fi
echo

echo "== Summary =="
if [[ "$failures" -eq 0 && "$warnings" -eq 0 ]]; then
  echo "All checks passed."
  exit 0
fi
if [[ "$failures" -eq 0 ]]; then
  echo "Passed with $warnings warning(s). Review [WARN] lines above."
  exit 0
fi
echo "Completed with $failures failure(s) and $warnings warning(s)."
exit 1
