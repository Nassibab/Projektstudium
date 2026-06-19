#!/bin/sh
set -e

MODEL_DIR="/app/models"
MODEL_FILE="${MODEL_DIR}/professor_synthetic_role_model.rds"

mkdir -p "${MODEL_DIR}"

if [ ! -f "${MODEL_FILE}" ] && [ -n "${MODEL_DOWNLOAD_URL}" ]; then
  echo "Model not found. Downloading from MODEL_DOWNLOAD_URL ..."
  curl -fsSL "${MODEL_DOWNLOAD_URL}" -o "${MODEL_FILE}.tmp"
  mv "${MODEL_FILE}.tmp" "${MODEL_FILE}"
  echo "Model saved to ${MODEL_FILE}"
elif [ ! -f "${MODEL_FILE}" ]; then
  echo "No model at ${MODEL_FILE}. Run GET /train-full-model or set MODEL_DOWNLOAD_URL."
fi

exec Rscript -e 'pr <- plumber::plumb("plumber.R"); pr$run(host="0.0.0.0", port=8000)'
