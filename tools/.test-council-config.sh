#!/usr/bin/env bash
# Validate tools/build_council_config.py against simulated inputs.
#
# Run whenever build_council_config.py or this script changes:
#   bash tools/.test-council-config.sh
#
# The generator is stdlib-only, so this harness needs only `python3`. To run
# inside the uv-managed environment (canonical for this repo), invoke as
#   uv run bash tools/.test-council-config.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="${REPO_ROOT}/tools/build_council_config.py"

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found on PATH" >&2
    exit 1
fi

PY=(python3)

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

PASS=0
FAIL=0

run_case() {
    local name="$1"
    local expected_exit="$2"
    local md_path="$3"
    local out_path="${TMPDIR}/${name}.json"
    local stderr_path="${TMPDIR}/${name}.stderr"

    set +e
    "${PY[@]}" "$SCRIPT" "$md_path" "$out_path" 2>"$stderr_path"
    local rc=$?
    set -e

    if [[ "$rc" == "$expected_exit" ]]; then
        printf "  PASS  %s (exit %d)\n" "$name" "$rc"
        PASS=$((PASS + 1))
    else
        printf "  FAIL  %s: expected exit %d, got %d\n" "$name" "$expected_exit" "$rc"
        echo "  stderr:" >&2
        sed 's/^/    /' "$stderr_path" >&2
        FAIL=$((FAIL + 1))
    fi
}

assert_stderr_contains() {
    local name="$1"
    local pattern="$2"
    local stderr_path="${TMPDIR}/${name}.stderr"
    if grep -q -- "$pattern" "$stderr_path"; then
        printf "  PASS  %s stderr contains '%s'\n" "$name" "$pattern"
        PASS=$((PASS + 1))
    else
        printf "  FAIL  %s stderr missing '%s'\n" "$name" "$pattern"
        echo "  actual stderr:" >&2
        sed 's/^/    /' "$stderr_path" >&2
        FAIL=$((FAIL + 1))
    fi
}

# ----------------------------------------------------------------------------
# Build a known-good baseline markdown; failure cases mutate copies of it.
# ----------------------------------------------------------------------------

BASE_MD="${TMPDIR}/base.md"
cat >"$BASE_MD" <<'EOF'
# Council Configuration

## Settings
search_provider: tavily
search_result_count: 8
full_content_results: 3
council_temperature: 0.5
chairman_temperature: 0.4
stage2_temperature: 0.3

## Enabled Providers
openrouter: true
ollama: false

## Direct Provider Toggles
openai: false
anthropic: false

## Council Models
- openrouter:anthropic/claude-opus-4.6
- openrouter:google/gemini-3.1-pro-preview

## Council Member Filters
(empty)

## Chairman Model
openrouter:anthropic/claude-opus-4.6

## Prompts

### Stage 1
````text
Question: {user_query}
Search: {search_context_block}
EOF
echo '````' >>"$BASE_MD"
cat >>"$BASE_MD" <<'EOF'

### Stage 2
````text
Question: {user_query}
Search: {search_context_block}
Responses: {responses_text}
EOF
echo '````' >>"$BASE_MD"
cat >>"$BASE_MD" <<'EOF'

### Stage 3
````text
Question: {user_query}
Search: {search_context_block}
Stage1: {stage1_text}
Stage2: {stage2_text}
EOF
echo '````' >>"$BASE_MD"

# ----------------------------------------------------------------------------
# Test cases
# ----------------------------------------------------------------------------

echo "Running build_council_config.py test suite..."

# 1. Happy path
run_case happy 0 "$BASE_MD"
"${PY[@]}" - <<'PY' "${TMPDIR}/happy.json"
import json, sys
d = json.load(open(sys.argv[1]))
assert d["council_models"], "council_models empty"
assert d["chairman_model"], "chairman_model empty"
assert "{user_query}" in d["prompts"]["stage1_prompt"]
assert "{responses_text}" in d["prompts"]["stage2_prompt"]
assert "{stage2_text}" in d["prompts"]["stage3_prompt"]
PY
echo "  PASS  happy structural assertions"
PASS=$((PASS + 1))

# 2. Missing Prompts section entirely → fail
MD="${TMPDIR}/no_prompts.md"
awk '/^## Prompts/{exit} {print}' "$BASE_MD" >"$MD"
run_case no_prompts 1 "$MD"
assert_stderr_contains no_prompts "stage1_prompt"

# 3. Stage 1 prompt missing {user_query}
MD="${TMPDIR}/missing_placeholder.md"
sed 's/Question: {user_query}/Question: PLACEHOLDER/' "$BASE_MD" >"$MD"
run_case missing_placeholder 1 "$MD"
assert_stderr_contains missing_placeholder "missing required placeholders"

# 4. Unknown placeholder in a prompt
MD="${TMPDIR}/unknown_placeholder.md"
sed 's/Question: {user_query}/Question: {user_quesry} {user_query}/' "$BASE_MD" >"$MD"
run_case unknown_placeholder 1 "$MD"
assert_stderr_contains unknown_placeholder "unknown placeholders"

# 5. council_models too few (1 entry)
MD="${TMPDIR}/too_few_models.md"
awk '
/^## Council Models/{print; in_models=1; next}
in_models && /^- / && count >= 1 {next}
in_models && /^- /{count++; print; next}
in_models && /^$/{in_models=0; print; next}
{print}
' "$BASE_MD" >"$MD"
run_case too_few_models 1 "$MD"
assert_stderr_contains too_few_models "between 2 and 8"

# 6. council_models too many (>8)
MD="${TMPDIR}/too_many_models.md"
awk '
/^## Council Models/{
  print
  for (i = 1; i <= 9; i++) print "- openrouter:vendor/model-" i
  in_models = 1
  next
}
in_models && /^- /{next}
in_models && /^$/{in_models=0; print; next}
{print}
' "$BASE_MD" >"$MD"
run_case too_many_models 1 "$MD"
assert_stderr_contains too_many_models "between 2 and 8"

# 7. Duplicate council models
MD="${TMPDIR}/dup_models.md"
awk '
/^## Council Models/{
  print
  print "- openrouter:anthropic/claude-opus-4.6"
  print "- openrouter:anthropic/claude-opus-4.6"
  in_models = 1
  next
}
in_models && /^- /{next}
in_models && /^$/{in_models=0; print; next}
{print}
' "$BASE_MD" >"$MD"
run_case dup_models 1 "$MD"
assert_stderr_contains dup_models "duplicate"

# 8. Missing chairman_model (empty section body)
MD="${TMPDIR}/no_chairman.md"
awk '
/^## Chairman Model/{print; print ""; skip = 1; next}
skip && /^## /{skip = 0}
skip{next}
{print}
' "$BASE_MD" >"$MD"
run_case no_chairman 1 "$MD"
assert_stderr_contains no_chairman "chairman_model"

# 9. Out-of-range temperature
MD="${TMPDIR}/bad_temp.md"
sed 's/^council_temperature: 0.5$/council_temperature: 5.0/' "$BASE_MD" >"$MD"
run_case bad_temp 1 "$MD"
assert_stderr_contains bad_temp "council_temperature"

# 10. Unknown h2 section (typo)
MD="${TMPDIR}/typo_section.md"
sed 's/^## Settings$/## Setings/' "$BASE_MD" >"$MD"
run_case typo_section 1 "$MD"
assert_stderr_contains typo_section "unknown section"

# ----------------------------------------------------------------------------

echo
echo "Results: ${PASS} passed, ${FAIL} failed"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
echo "All tests passed"
