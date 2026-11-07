FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY requirements-prosody.txt .
# CPU inference only: PyPI Torch also pulls large CUDA dependencies on Linux.
# Keep this version aligned with requirements-prosody.txt.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "torch==2.14.1+cpu" --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements-prosody.txt \
    && python -c "import torch; assert torch.version.cuda is None, 'CPU-only Torch required'"
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
EXPOSE 8100
CMD ["sh", "-c", "python -m app.bootstrap_db && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8100"]
