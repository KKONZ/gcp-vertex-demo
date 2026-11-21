# Build from the repo root so this can reach data/personas.json:
#   docker build -f services/agent/Dockerfile -t agent .
#
# personas.json being baked into the image (rather than mounted) is a
# placeholder for this milestone -- becomes a ConfigMap/volume mount once
# this is actually deployed to Kubernetes.
FROM python:3.12-slim

WORKDIR /app

COPY services/agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/agent/app ./app
COPY data/personas.json ./data/personas.json

ENV PYTHONUNBUFFERED=1
ENV PERSONAS_PATH=/app/data/personas.json
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
