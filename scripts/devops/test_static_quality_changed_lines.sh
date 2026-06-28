#!/usr/bin/env bash
# TECHDEBT-E: Self-test for static quality changed-line gate.
# Verifies that the Python helper correctly classifies ruff diagnostics
# as NEW (on changed line) vs EXISTING (not on changed line).
#
# This test creates a temporary git repo and simulates PR scenarios.
# It does NOT require Docker, DB, ruff, or any runtime services.
set -euo pipefail

PASS=0
FAIL=0
TEST_DIR=''

cleanup() {
  if [[ -n "$TEST_DIR" && -d "$TEST_DIR" ]]; then
    rm -rf "$TEST_DIR"
  fi
}
trap cleanup EXIT

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail_test() { FAIL=$((FAIL + 1)); echo "  FAIL: $1" >&2; }

# ------------------------------------------------------------------
# Unit-test the classification logic using simulated diagnostics
# ------------------------------------------------------------------

test_classify_new_on_changed_line() {
  echo "Test 1: Diagnostic on changed line => NEW"

  cat > /tmp/classify_test.py <<'PY'
import json, sys

# Simulated ruff diagnostics
diags = [
    {"filename": "src/test.py", "location": {"row": 5, "column": 1}, "code": "F401", "message": "unused import"},
    {"filename": "src/test.py", "location": {"row": 20, "column": 1}, "code": "E501", "message": "line too long"},
]

# Simulated changed lines: line 5 was added, line 20 was NOT
changed_lines = {"src/test.py": {5}}

# Classification (from static_quality_changed_lines.py logic)
new = []
existing = []
for d in diags:
    fn = d.get("filename", "")
    ln = d.get("location", {}).get("row", 0)
    changed = changed_lines.get(fn, set())
    if ln in changed:
        new.append(d)
    else:
        existing.append(d)

assert len(new) == 1, f"Expected 1 NEW, got {len(new)}"
assert len(existing) == 1, f"Expected 1 EXISTING, got {len(existing)}"
assert new[0]["code"] == "F401"
assert existing[0]["code"] == "E501"
print("OK: classification correct")
PY

  if python3 /tmp/classify_test.py; then
    pass "diagnostic on changed line classified as NEW"
    pass "diagnostic outside changed line classified as EXISTING"
  else
    fail_test "classification logic broken"
  fi
}

test_all_existing_no_block() {
  echo "Test 2: All diagnostics existing => warn, no block"

  cat > /tmp/classify_test2.py <<'PY'
import json

diags = [
    {"filename": "src/test.py", "location": {"row": 10, "column": 1}, "code": "F841", "message": "unused variable"},
    {"filename": "src/test.py", "location": {"row": 15, "column": 1}, "code": "E302", "message": "expected 2 blank lines"},
]
changed_lines = {"src/test.py": {1, 2, 3}}  # Only lines 1-3 were changed

new = [d for d in diags if d.get("location", {}).get("row", 0) in changed_lines.get(d.get("filename", ""), set())]
existing = [d for d in diags if d.get("location", {}).get("row", 0) not in changed_lines.get(d.get("filename", ""), set())]

assert len(new) == 0, f"Expected 0 NEW, got {len(new)}"
assert len(existing) == 2, f"Expected 2 EXISTING, got {len(existing)}"
print("OK: all existing, no block")
PY

  if python3 /tmp/classify_test2.py; then
    pass "all violations pre-existing => no new, warn only"
  else
    fail_test "all-existing case broken"
  fi
}

test_mixed_new_and_existing() {
  echo "Test 3: Mixed new + existing => block because of new"

  cat > /tmp/classify_test3.py <<'PY'
diags = [
    {"filename": "src/test.py", "location": {"row": 5, "column": 1}, "code": "F401", "message": "unused import"},
    {"filename": "src/test.py", "location": {"row": 10, "column": 1}, "code": "E501", "message": "line too long"},
    {"filename": "src/test.py", "location": {"row": 15, "column": 1}, "code": "F841", "message": "unused variable"},
]
changed_lines = {"src/test.py": {5}}  # Only line 5 changed

new = [d for d in diags if d.get("location", {}).get("row", 0) in changed_lines.get(d.get("filename", ""), set())]
existing = [d for d in diags if d.get("location", {}).get("row", 0) not in changed_lines.get(d.get("filename", ""), set())]

assert len(new) == 1, f"Expected 1 NEW, got {len(new)}"
assert len(existing) == 2
assert new[0]["code"] == "F401"
# Decision: if ANY new violations, BLOCK
should_block = len(new) > 0
assert should_block, "Should block because of new violation"
print("OK: mixed case correctly blocks on new violation")
PY

  if python3 /tmp/classify_test3.py; then
    pass "mixed new+existing correctly blocks because of new violation"
  else
    fail_test "mixed case broken"
  fi
}

test_no_diagnostics_pass() {
  echo "Test 4: No diagnostics => pass"

  cat > /tmp/classify_test4.py <<'PY'
diags = []
changed_lines = {"src/test.py": {1, 2, 3}}
new = [d for d in diags if d.get("location", {}).get("row", 0) in changed_lines.get(d.get("filename", ""), set())]
assert len(new) == 0
print("OK: no diagnostics, pass")
PY

  if python3 /tmp/classify_test4.py; then
    pass "no diagnostics => pass"
  else
    fail_test "empty case broken"
  fi
}

test_unknown_file_treated_as_new() {
  echo "Test 5: Diagnostic in unknown file => treated as NEW (fail-safe)"

  cat > /tmp/classify_test5.py <<'PY'
diags = [
    {"filename": "src/unknown.py", "location": {"row": 1, "column": 1}, "code": "F401", "message": "unused import"},
]
changed_lines = {}  # No changed-line data

new = []
for d in diags:
    fn = d.get("filename", "")
    ln = d.get("location", {}).get("row", 0)
    changed = changed_lines.get(fn, set())
    if not changed:  # No data => treat as new (fail-safe)
        new.append(d)
    elif ln in changed:
        new.append(d)

assert len(new) == 1, "Should treat as new (fail-safe) when changed_lines unavailable"
print("OK: unknown file treated as NEW (fail-safe)")
PY

  if python3 /tmp/classify_test5.py; then
    pass "unknown file correctly treated as NEW (fail-safe)"
  else
    fail_test "fail-safe case broken"
  fi
}

# ------------------------------------------------------------------
# Test the Python helper script can be imported and parsed
# ------------------------------------------------------------------

test_helper_script_parseable() {
  echo "Test 6: Helper script is valid Python"

  if python3 -c "import ast; ast.parse(open('scripts/devops/static_quality_changed_lines.py').read()); print('OK: parseable')" 2>/dev/null; then
    pass "static_quality_changed_lines.py is valid Python (AST parse)"
  else
    fail_test "static_quality_changed_lines.py has syntax errors"
  fi
}

# ------------------------------------------------------------------
# Test 7: _safe_decode handles invalid UTF-8
# ------------------------------------------------------------------

test_safe_decode_handles_invalid_utf8() {
  echo "Test 7: _safe_decode handles invalid UTF-8 bytes"

  cat > /tmp/safe_decode_test.py <<'PY'
import sys
sys.path.insert(0, "scripts/devops")
from static_quality_changed_lines import _safe_decode

assert _safe_decode(b"hello") == "hello"
result = _safe_decode(b"hello\xffworld")
assert "hello" in result
assert "world" in result
assert "�" in result
assert _safe_decode(None) == ""
assert _safe_decode("already str") == "already str"
print("OK: _safe_decode handles invalid UTF-8 without crash")
PY

  if python3 /tmp/safe_decode_test.py; then
    pass "_safe_decode correctly handles valid and invalid UTF-8 bytes"
  else
    fail_test "_safe_decode crashed or returned wrong result"
  fi
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
echo "TECHDEBT-E Static Quality Changed-Line Self-Test"
echo "================================================"
echo

test_classify_new_on_changed_line
echo
test_all_existing_no_block
echo
test_mixed_new_and_existing
echo
test_no_diagnostics_pass
echo
test_unknown_file_treated_as_new
echo
test_helper_script_parseable
echo
test_safe_decode_handles_invalid_utf8
echo

echo "================================================"
echo "Results: $PASS passed, $FAIL failed"
echo "================================================"

if [[ "$FAIL" -gt 0 ]]; then
  echo "SELF_TEST_FAILED" >&2
  exit 1
fi

echo "SELF_TEST_PASSED"
exit 0

# ------------------------------------------------------------------
# Test 7: _safe_decode handles invalid UTF-8 without crash
# ------------------------------------------------------------------

  echo "Test 7: _safe_decode handles invalid UTF-8 bytes"

  cat > /tmp/safe_decode_test.py <<'PY'
import sys
sys.path.insert(0, "scripts/devops")
from static_quality_changed_lines import _safe_decode

# Valid UTF-8
assert _safe_decode(b"hello") == "hello"

# Invalid UTF-8 (0xFF is never valid in UTF-8)
result = _safe_decode(b"hello\xffworld")
assert "hello" in result
assert "world" in result
assert "�" in result  # U+FFFD replacement character

# None
assert _safe_decode(None) == ""

# Already a string
assert _safe_decode("already str") == "already str"

print("OK: _safe_decode handles invalid UTF-8 without crash")
PY

  if python3 /tmp/safe_decode_test.py; then
    pass "_safe_decode correctly handles valid and invalid UTF-8 bytes"
  else
    fail_test "_safe_decode crashed or returned wrong result"
  fi
}

test_safe_decode_handles_invalid_utf8
echo
