#!/usr/bin/env bash
# Deploy VeriEarth (API + web) to Cloud Run.
#
# Prerequisites (one-time, by the project owner):
#   gcloud auth login
#   export PROJECT=<your-gcp-project-id>      # billing enabled
#   export GEMINI_API_KEY=<key from AI Studio>
#
# Usage:  bash deploy.sh
set -euo pipefail

PROJECT="${PROJECT:?set PROJECT to your GCP project id}"
REGION="${REGION:-asia-southeast1}"
REPO="${REPO:-veriearth}"
TAG="$(date +%Y%m%d-%H%M%S)"
REG="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}"

gcloud config set project "$PROJECT" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com aiplatform.googleapis.com >/dev/null

gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "$REPO" --repository-format docker --location "$REGION"

# Gemini key as a secret (never baked into images).
if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  if gcloud secrets describe gemini-api-key >/dev/null 2>&1; then
    printf '%s' "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=- >/dev/null
  else
    printf '%s' "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=- >/dev/null
  fi
  PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
  gcloud secrets add-iam-policy-binding gemini-api-key \
    --member "serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role roles/secretmanager.secretAccessor >/dev/null
  SECRET_FLAG=(--set-secrets "GEMINI_API_KEY=gemini-api-key:latest")
else
  echo "WARNING: GEMINI_API_KEY not set; agent and intake endpoints will report Gemini as unconfigured."
  SECRET_FLAG=()
fi

echo "== API =="
gcloud builds submit backend --config backend/cloudbuild.veri.yaml --substitutions "_IMAGE=${REG}/veri-api:${TAG}"
gcloud run deploy veri-api --image "${REG}/veri-api:${TAG}" --region "$REGION" --allow-unauthenticated \
  --memory 2Gi --cpu 2 --min-instances 1 --timeout 300 "${SECRET_FLAG[@]}"
API_URL="$(gcloud run services describe veri-api --region "$REGION" --format='value(status.url)')"

echo "== Web =="
gcloud builds submit web --config web/cloudbuild.yaml \
  --substitutions "_IMAGE=${REG}/veri-web:${TAG},_API_URL=${API_URL}"
gcloud run deploy veri-web --image "${REG}/veri-web:${TAG}" --region "$REGION" --allow-unauthenticated \
  --memory 512Mi --min-instances 1
WEB_URL="$(gcloud run services describe veri-web --region "$REGION" --format='value(status.url)')"

# Lock CORS to the web origin.
gcloud run services update veri-api --region "$REGION" --update-env-vars "VERI_CORS_ORIGINS=${WEB_URL}" >/dev/null

echo
echo "API: ${API_URL}"
echo "Web: ${WEB_URL}"
