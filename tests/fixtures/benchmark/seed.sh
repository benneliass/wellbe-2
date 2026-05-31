#!/usr/bin/env bash
# Seed benchmark fixture data into the ingestion-worker.
# Usage:
#   bash seed.sh [--mode blind_pre_diagnosis|full_results_no_final_label] [--case C01]
#
# Environment:
#   INGESTION_WORKER_URL  default: http://localhost:8003

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/manifest.yaml"
INGESTION_WORKER_URL="${INGESTION_WORKER_URL:-http://localhost:8003}"

MODE="blind_pre_diagnosis"
FILTER_CASE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"; shift 2 ;;
    --case)
      FILTER_CASE="$2"; shift 2 ;;
    *)
      echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ "$MODE" != "blind_pre_diagnosis" && "$MODE" != "full_results_no_final_label" ]]; then
  echo "Error: --mode must be 'blind_pre_diagnosis' or 'full_results_no_final_label'" >&2
  exit 1
fi

# Parse manifest.yaml with python3 (yq may not be available)
CASES_JSON=$(python3 -c "
import yaml, json

with open('${MANIFEST}') as f:
    manifest = yaml.safe_load(f)

cases = []
for c in manifest.get('cases', []):
    cases.append({
        'case_id': c['case_id'],
        'synthetic_user_id': c['synthetic_user_id'],
        'case_dir': c['case_dir'],
    })
print(json.dumps(cases))
")

TOTAL_SENT=0
TOTAL_FAILED=0

process_case() {
  local CASE_ID="$1"
  local USER_ID="$2"
  local CASE_DIR_REL="$3"

  local EVENTS_DIR="${SCRIPT_DIR}/${CASE_DIR_REL}/${MODE}/raw_events"

  if [[ ! -d "$EVENTS_DIR" ]]; then
    echo "[${CASE_ID}] WARNING: events dir not found: ${EVENTS_DIR}" >&2
    return
  fi

  # Sort files by filename (natural order)
  mapfile -t EVENT_FILES < <(ls "${EVENTS_DIR}"/*.json 2>/dev/null | sort)

  local TOTAL_FILES=${#EVENT_FILES[@]}
  local IDX=0

  for EVENT_FILE in "${EVENT_FILES[@]}"; do
    IDX=$((IDX + 1))
    local FILENAME
    FILENAME=$(basename "$EVENT_FILE")

    # Extract event type from filename (e.g. 00000_timeline_history.json -> timeline_history)
    local EVENT_TYPE
    EVENT_TYPE=$(echo "$FILENAME" | sed 's/^[0-9]*_//' | sed 's/\.json$//')

    # Parse event JSON with python3
    local PAYLOAD
    PAYLOAD=$(python3 -c "
import json, base64, sys, uuid

with open('${EVENT_FILE}') as f:
    ev = json.load(f)

captured_at = ev.get('captured_at', '')
user_id = '${USER_ID}'

# Extract text: try raw_payload.original.event, then raw_payload as JSON string
raw_payload = ev.get('raw_payload', {})
if isinstance(raw_payload, dict):
    original = raw_payload.get('original', {})
    if isinstance(original, dict) and 'event' in original:
        text = original['event']
    else:
        text = json.dumps(raw_payload)
else:
    text = str(raw_payload)

raw_data = base64.b64encode(text.encode('utf-8')).decode('utf-8')

payload = {
    'source_type': 'manual_text',
    'raw_data': raw_data,
    'captured_at': captured_at,
    'actor_id': user_id,
    'patient_id': user_id,
    'consent_snapshot_id': str(uuid.uuid4()),
    'correlation_id': str(uuid.uuid4()),
    'trace_id': str(uuid.uuid4()),
    'metadata': {
        'text': text,
        'case_id': '${CASE_ID}',
        'event_file': '${FILENAME}',
    }
}
print(json.dumps(payload))
" 2>&1)

    if [[ $? -ne 0 ]]; then
      printf "[%s] %03d/%03d %s → ERROR (payload build failed)\n" "$CASE_ID" "$IDX" "$TOTAL_FILES" "$EVENT_TYPE" >&2
      TOTAL_FAILED=$((TOTAL_FAILED + 1))
      continue
    fi

    local HTTP_STATUS
    HTTP_STATUS=$(echo "$PAYLOAD" | curl -s -o /dev/null -w "%{http_code}" \
      -X POST "${INGESTION_WORKER_URL}/ingest" \
      -H "Content-Type: application/json" \
      -d @-)

    if [[ "$HTTP_STATUS" == "200" || "$HTTP_STATUS" == "201" || "$HTTP_STATUS" == "202" ]]; then
      printf "[%s] %03d/%03d %s → %s OK\n" "$CASE_ID" "$IDX" "$TOTAL_FILES" "$EVENT_TYPE" "$HTTP_STATUS"
      TOTAL_SENT=$((TOTAL_SENT + 1))
    else
      printf "[%s] %03d/%03d %s → %s FAILED\n" "$CASE_ID" "$IDX" "$TOTAL_FILES" "$EVENT_TYPE" "$HTTP_STATUS" >&2
      TOTAL_FAILED=$((TOTAL_FAILED + 1))
    fi
  done
}

# Iterate over cases from manifest JSON
CASE_COUNT=$(echo "$CASES_JSON" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")

for i in $(seq 0 $((CASE_COUNT - 1))); do
  CASE_ID=$(echo "$CASES_JSON" | python3 -c "import json,sys; cases=json.load(sys.stdin); print(cases[${i}]['case_id'])")
  SYNTHETIC_USER_ID=$(echo "$CASES_JSON" | python3 -c "import json,sys; cases=json.load(sys.stdin); print(cases[${i}]['synthetic_user_id'])")
  CASE_DIR_REL=$(echo "$CASES_JSON" | python3 -c "import json,sys; cases=json.load(sys.stdin); print(cases[${i}]['case_dir'])")

  if [[ -n "$FILTER_CASE" && "$CASE_ID" != "$FILTER_CASE" ]]; then
    continue
  fi

  echo ""
  echo "=== Seeding ${CASE_ID} (mode: ${MODE}) | user: ${SYNTHETIC_USER_ID} ==="
  process_case "$CASE_ID" "$SYNTHETIC_USER_ID" "$CASE_DIR_REL"
done

echo ""
echo "=== Summary ==="
echo "Total sent:  ${TOTAL_SENT}"
echo "Total failed: ${TOTAL_FAILED}"

if [[ "$TOTAL_FAILED" -gt 0 ]]; then
  exit 1
fi
