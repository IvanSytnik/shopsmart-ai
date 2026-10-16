#!/usr/bin/env bash
# Changes only CORS_ORIGINS on the running Cloud Run service (creates a new revision;
# other env vars and the secret are kept).
#
#   PROJECT_ID=my-project CORS_ORIGINS=https://shopsmart.sytnik-studio.com,https://shopsmart-ai.pages.dev \
#     ./deploy/update_cors.sh
#
# Env: PROJECT_ID (required), CORS_ORIGINS (required, comma-separated),
#      REGION (default europe-west1), SERVICE (default shopsmart-api).
set -euo pipefail

: "${PROJECT_ID:?set PROJECT_ID to the GCP project id}"
: "${CORS_ORIGINS:?set CORS_ORIGINS to the frontend origin(s), comma-separated}"
REGION="${REGION:-europe-west1}"
SERVICE="${SERVICE:-shopsmart-api}"

if [[ "$CORS_ORIGINS" == *@* ]]; then
  echo "CORS_ORIGINS must not contain '@' (used as the env var delimiter)" >&2
  exit 1
fi

# "^@^" makes "@" the list delimiter, so the commas stay inside the single value.
gcloud run services update "$SERVICE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --update-env-vars "^@^CORS_ORIGINS=$CORS_ORIGINS"

gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT_ID" \
  --format 'value(status.url)'
