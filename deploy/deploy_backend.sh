#!/usr/bin/env bash
# Builds backend/ with Cloud Build and deploys it to Cloud Run. See deploy/README.md.
#
#   PROJECT_ID=my-project CORS_ORIGINS=https://shopsmart.sytnik-studio.com ./deploy/deploy_backend.sh
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

cd "$(dirname "$0")/.."

# --max-instances 1 is intentional: RATE_LIMIT (slowapi) and DAILY_GENERATE_CAP are kept
# in memory per process, so a second instance would double both limits and the OpenAI
# spend they protect. Raise it only after moving those counters to a shared store.
#
# "^@^" switches gcloud's list delimiter from "," to "@" so the comma-separated
# CORS_ORIGINS stays one value. FORWARDED_ALLOW_IPS=* is safe here: the container is
# reachable only through Google's front end, which sets X-Forwarded-For, and the rate
# limit keys on the client IP from that header.
gcloud run deploy "$SERVICE" \
  --source backend \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --concurrency 20 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --set-secrets OPENAI_API_KEY=openai-api-key:latest \
  --set-env-vars "^@^ENVIRONMENT=production@CORS_ORIGINS=$CORS_ORIGINS@RATE_LIMIT=10/minute@DAILY_GENERATE_CAP=200@FORWARDED_ALLOW_IPS=*"

url="$(gcloud run services describe "$SERVICE" \
  --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')"
echo "Service URL: $url"

echo "GET $url/health"
curl -fsS --retry 3 --retry-delay 2 "$url/health"
echo
