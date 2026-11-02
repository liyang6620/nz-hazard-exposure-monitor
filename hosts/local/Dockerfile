FROM node:22.19.0-bookworm-slim AS frontend

WORKDIR /workspace/frontend
ARG VITE_LINZ_LDS_TILES_API_KEY=""
ENV VITE_LINZ_LDS_TILES_API_KEY=${VITE_LINZ_LDS_TILES_API_KEY}
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/src

WORKDIR /workspace

COPY requirements-local.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements-local.txt

COPY src ./src
COPY hosts ./hosts
COPY scripts ./scripts
COPY --from=frontend /workspace/frontend/dist ./frontend-dist

RUN useradd --create-home --uid 10001 nzhem \
    && mkdir -p /data /state \
    && HOME=/home/nzhem python -c "import duckdb; c=duckdb.connect(); c.execute('INSTALL spatial'); c.execute('INSTALL h3 FROM community')" \
    && chown -R nzhem:nzhem /workspace /data /state

USER nzhem

EXPOSE 8000
CMD ["uvicorn", "hosts.local.app:app", "--host", "0.0.0.0", "--port", "8000"]

