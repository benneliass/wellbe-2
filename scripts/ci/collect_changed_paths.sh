#!/usr/bin/env bash
# Print changed paths, one per line, for classify_changes.py.
#
# Prints a single "#unknown" line when the diff base is not in this clone
# (new branch, force-push, manual dispatch). The classifier then runs every
# module. Guessing "nothing changed" would skip the tests.
set -euo pipefail

event="${EVENT_NAME:?EVENT_NAME is required}"
head="${HEAD_SHA:?HEAD_SHA is required}"

if [[ "$event" == "workflow_dispatch" ]]; then
  echo "#unknown"
  exit 0
fi

if [[ "$event" == "pull_request" ]]; then
  base="${BASE_SHA:?BASE_SHA is required for pull_request}"
elif [[ "$event" == "push" ]]; then
  base="${BEFORE_SHA:?BEFORE_SHA is required for push}"
  if [[ "$base" == "0000000000000000000000000000000000000000" ]]; then
    echo "#unknown"
    exit 0
  fi
else
  echo "#unknown"
  exit 0
fi

if ! git rev-parse --verify --quiet "${base}^{commit}" >/dev/null; then
  echo "#unknown"
  exit 0
fi
if ! git rev-parse --verify --quiet "${head}^{commit}" >/dev/null; then
  echo "#unknown"
  exit 0
fi

git diff --name-only --find-renames "$base" "$head"
