# Build from the repo root:
#   docker build -f services/agent/Dockerfile -t agent .
#
# personas.json is NOT baked in -- it's mounted at /app/data/personas.json
# from a ConfigMap (see infra/k8s/base/agent-configmap.yaml). Without that
# mount (e.g. a bare `docker run`), _load_personas() just returns {}.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY services/agent/requirements.txt .
# Cache mount persists uv's wheel cache across builds (unlike plain `pip
# install --no-cache-dir`), so a requirements.txt change doesn't re-download
# torch etc. from scratch every time -- the main reason rebuilds here were slow.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

COPY services/agent/app ./app

ENV PYTHONUNBUFFERED=1
ENV PERSONAS_PATH=/app/data/personas.json
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
