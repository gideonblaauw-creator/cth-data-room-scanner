#!/usr/bin/env bash
# Static smoke checks for Scanner Understanding Lab (LexiScan house tour).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

fail=0
check() {
  if eval "$2"; then
    echo "OK  $1"
  else
    echo "FAIL $1"
    fail=1
  fi
}

for f in index.html app.js data.js styles.css README.md defaults/findings-hitl-20260908-214515.json; do
  check "file exists: $f" "test -f '$f'"
done

check "data.js defines PLAYGROUND_DATA" "grep -q 'window.PLAYGROUND_DATA' data.js"
check "data.js uses nameEn/nameEs" "grep -q 'nameEn' data.js && grep -q 'nameEs' data.js"
check "data.js lexiscan format tag" "grep -q 'lexiscan-house-tour-v1' data.js"
check "app.js references floor plan" "grep -q 'floor-plan' app.js"
check "app.js ledger markdown export" "grep -q 'buildLedgerMarkdown' app.js"
check "index.html loads split assets" "grep -q 'data.js' index.html && grep -q 'app.js' index.html && grep -q 'styles.css' index.html"
check "no embedded Notion token values" "! grep -Eiq 'ntn_|secret_.*notion|notion_api_token=' index.html app.js data.js"
check "defaults findings valid JSON" "python3 -c \"import json; json.load(open('defaults/findings-hitl-20260908-214515.json'))\""
check "defaults has gate_findings" "python3 -c \"import json; d=json.load(open('defaults/findings-hitl-20260908-214515.json')); assert len(d.get('gate_findings',[]))>=5\""

echo "---"
if [[ "$fail" -eq 0 ]]; then
  echo "smoke: PASS"
  exit 0
else
  echo "smoke: FAIL"
  exit 1
fi
