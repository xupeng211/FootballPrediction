#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATEKEEPER="$ROOT_DIR/scripts/devops/gatekeeper.sh"
zero=0000000000000000000000000000000000000000
old=1111111111111111111111111111111111111111
new=2222222222222222222222222222222222222222
eval "$(sed -n '/^classify_ref_updates()/,/^}/p' "$GATEKEEPER")"
classify() {
  REF_TRANSACTION_CLASS=SOURCE_UPDATING_PUSH
  local input_file
  input_file=$(mktemp)
  if [[ -n "$1" ]]; then printf '%s\n' "$1" >"$input_file"; fi
  classify_ref_updates <"$input_file"
  rm -f "$input_file"
  printf '%s\n' "$REF_TRANSACTION_CLASS"
}
expect() {
  local name=$1 expected=$2 input=$3 actual
  actual=$(classify "$input")
  [[ "$actual" == "$expected" ]] || { echo "FAIL $name: $actual != $expected" >&2; exit 1; }
  echo "PASS $name"
}
expect single-delete PURE_REF_DELETE "(delete) $zero refs/heads/a $old"
expect multi-delete PURE_REF_DELETE $'(delete) '$zero' refs/heads/a '$old$'\n(delete) '$zero' refs/heads/b '$old
expect normal-update SOURCE_UPDATING_PUSH "refs/heads/a $old refs/heads/a $new"
expect new-branch SOURCE_UPDATING_PUSH "refs/heads/a $new refs/heads/a $zero"
expect mixed-update SOURCE_UPDATING_PUSH $'(delete) '$zero' refs/heads/a '$old$'\nrefs/heads/b '$old' refs/heads/b '$new
expect mixed-new SOURCE_UPDATING_PUSH $'(delete) '$zero' refs/heads/a '$old$'\nrefs/heads/b '$new' refs/heads/b '$zero
expect malformed INVALID_OR_UNPARSEABLE_INPUT "not-a-ref-line"
expect zero-zero INVALID_OR_UNPARSEABLE_INPUT "(delete) $zero refs/heads/a $zero"
expect empty NO_REF_UPDATES ""
echo 'PASS ref-delete policy matrix'
