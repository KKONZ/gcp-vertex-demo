#!/usr/bin/env bash
# (Re)creates the agent-personas ConfigMap from the locally generated
# data/personas.json (see README step 3 -- gitignored, not baked into any
# image or kustomization). Run before `kubectl apply -k` the first time, and
# again any time personas.json changes.
set -euo pipefail

NAMESPACE="${1:-vertex-demo}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PERSONAS_FILE="$REPO_ROOT/data/personas.json"

if [[ ! -f "$PERSONAS_FILE" ]]; then
  echo "Missing $PERSONAS_FILE -- run 'python data/scripts/sample_personas.py' first." >&2
  exit 1
fi

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl create configmap agent-personas \
  --from-file=personas.json="$PERSONAS_FILE" \
  --namespace "$NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -
