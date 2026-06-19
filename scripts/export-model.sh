#!/usr/bin/env bash
# Copy the trained model from the analyse-r container to the host for upload.
#
# Usage:
#   ./scripts/export-model.sh
#   ./scripts/upload-model-release.sh model-v1

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

CONTAINER="${ANALYSE_R_CONTAINER:-psb1-127-analyse-r-1}"
REMOTE="/app/models/professor_synthetic_role_model.rds"
LOCAL="services/analyse-r/models/professor_synthetic_role_model.rds"

mkdir -p "$(dirname "${LOCAL}")"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "Error: container ${CONTAINER} is not running." >&2
  echo "Start it with: docker compose up -d analyse-r" >&2
  exit 1
fi

if ! docker exec "${CONTAINER}" test -f "${REMOTE}"; then
  echo "Error: no model in container at ${REMOTE}" >&2
  echo "Train first: curl http://localhost:8020/train-full-model" >&2
  exit 1
fi

docker cp "${CONTAINER}:${REMOTE}" "${LOCAL}"
echo "Exported to ${LOCAL} ($(du -h "${LOCAL}" | cut -f1))"
