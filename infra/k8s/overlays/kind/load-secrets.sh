#!/usr/bin/env bash
# Creates the two real-credential Secrets the kind overlay needs, reusing
# exactly what local dev already has on disk -- the .env OPENAI_API_KEY and
# the developer's own `gcloud auth application-default login` ADC file. Never
# printed: this script only passes them to `kubectl create`, whose own output
# is just "secret/x created".
set -euo pipefail

NAMESPACE="${1:-vertex-demo}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
# services/agent/.env carries the real key; the repo-root .env is a stale
# duplicate with OPENAI_API_KEY left blank -- prefer whichever actually has it.
ENV_FILE="$REPO_ROOT/services/agent/.env"
if [[ ! -s "$ENV_FILE" ]] || ! grep -q "^OPENAI_API_KEY=.\+" "$ENV_FILE" 2>/dev/null; then
  ENV_FILE="$REPO_ROOT/.env"
fi
ADC_FILE="${APPDATA:-$HOME/.config}/gcloud/application_default_credentials.json"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi
if [[ ! -f "$ADC_FILE" ]]; then
  echo "Missing $ADC_FILE -- run 'gcloud auth application-default login' first." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY not set in $ENV_FILE" >&2
  exit 1
fi

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl delete secret agent-secrets -n "$NAMESPACE" --ignore-not-found >/dev/null
kubectl create secret generic agent-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --namespace "$NAMESPACE" >/dev/null

kubectl delete secret adc-credentials -n "$NAMESPACE" --ignore-not-found >/dev/null
kubectl create secret generic adc-credentials \
  --from-file=application_default_credentials.json="$ADC_FILE" \
  --namespace "$NAMESPACE" >/dev/null

echo "agent-secrets and adc-credentials created in namespace $NAMESPACE"
