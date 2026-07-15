# --- build stage --------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip build \
 && python -m build --wheel --outdir /wheels .

# --- runtime stage ------------------------------------------------------
FROM python:3.12-slim

# Non-root user so the container is safe to run in Kubernetes as-is.
RUN groupadd --system app && useradd --system --gid app --home /home/app --create-home app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl \
 && rm -rf /wheels

USER app
WORKDIR /home/app

# Config lives here; mount a volume if you want it to survive restarts.
ENV XDG_CONFIG_HOME=/home/app/.config \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["loki-cli"]
CMD ["--help"]
