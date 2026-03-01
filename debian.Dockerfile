# Stage 1: Build
FROM debian:12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv python3-dev build-essential && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir build

WORKDIR /app
COPY . /app
RUN pip install . && python3 -m build --wheel

# Stage 2: Run
FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip python3-venv && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY --from=builder /app/dist/*.whl ./
RUN pip install --no-cache-dir ./*.whl

EXPOSE 8080
ENTRYPOINT ["cdd-python", "server_json_rpc", "--listen", "0.0.0.0", "--port", "8080"]
