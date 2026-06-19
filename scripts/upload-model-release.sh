#!/usr/bin/env bash
# Upload professor_synthetic_role_model.rds to a GitHub Release.
#
# Usage:
#   export GITHUB_TOKEN=ghp_...   # needs repo scope
#   ./scripts/upload-model-release.sh [tag] [release_name]
#
# Example:
#   ./scripts/upload-model-release.sh model-v1 "Professor synthetic role model"

set -euo pipefail

REPO="${GITHUB_REPOSITORY:-Nassibab/Projektstudium}"
TAG="${1:-model-v1}"
RELEASE_NAME="${2:-Professor synthetic role model}"
MODEL_PATH="services/analyse-r/models/professor_synthetic_role_model.rds"
ASSET_NAME="professor_synthetic_role_model.rds"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "Error: set GITHUB_TOKEN (GitHub PAT with repo scope)." >&2
  exit 1
fi

if [ ! -f "${MODEL_PATH}" ]; then
  echo "Error: model file not found at ${MODEL_PATH}" >&2
  echo "Train first: curl http://localhost:8020/train-full-model" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

API="https://api.github.com/repos/${REPO}/releases"

echo "Creating release ${TAG} on ${REPO} ..."
RELEASE_JSON=$(curl -fsSL -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "${API}" \
  -d "{\"tag_name\":\"${TAG}\",\"name\":\"${RELEASE_NAME}\",\"body\":\"Pre-trained ranger TF-IDF model for analyse-r\"}")

RELEASE_ID=$(echo "${RELEASE_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Uploading ${MODEL_PATH} ($(du -h "${MODEL_PATH}" | cut -f1)) ..."
UPLOAD_URL="https://uploads.github.com/repos/${REPO}/releases/${RELEASE_ID}/assets?name=${ASSET_NAME}"

curl -fsSL -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @"${MODEL_PATH}" \
  "${UPLOAD_URL}" > /dev/null

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET_NAME}"

echo ""
echo "Upload complete."
echo "Download URL:"
echo "  ${DOWNLOAD_URL}"
echo ""
echo "Add to .env:"
echo "  MODEL_DOWNLOAD_URL=${DOWNLOAD_URL}"
