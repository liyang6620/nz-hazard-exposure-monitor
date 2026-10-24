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

RUN useradd --create-home --uid 10001 nzhem \
    && mkdir -p /data /state \
    && HOME=/home/nzhem python -c "import duckdb; c=duckdb.connect(); c.execute('INSTALL spatial'); c.execute('INSTALL h3 FROM community')" \
    && chown -R nzhem:nzhem /workspace /data /state

USER nzhem

EXPOSE 8000
CMD ["uvicorn", "hosts.local.app:app", "--host", "0.0.0.0", "--port", "8000"]

