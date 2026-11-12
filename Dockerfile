# Linux amd64/Python 3.12 lock target; provenance in requirements/provenance.json.
FROM python:3.12-slim@sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    OMP_NUM_THREADS=2 \
    MKL_NUM_THREADS=2 \
    HF_HOME=/models/huggingface
WORKDIR /app
COPY requirements/ requirements/
RUN python -m pip install --no-cache-dir --require-hashes -r requirements/build.lock \
    && python -m pip install --no-cache-dir --require-hashes -r requirements/local-models.lock --extra-index-url https://download.pytorch.org/whl/cpu
COPY pyproject.toml alembic.ini ./
COPY src/ src/
COPY migrations/ migrations/
COPY scripts/models/ scripts/models/
RUN python -m pip install --no-deps --no-build-isolation .
USER 10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
