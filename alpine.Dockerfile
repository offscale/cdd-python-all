# Stage 1: Build
FROM alpine:3.21 AS builder

RUN apk update && apk add --no-cache python3 py3-pip python3-dev build-base
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir uv build

WORKDIR /app
COPY . /app
RUN pip install . && python3 -m build --wheel

# Stage 2: Run
FROM alpine:3.21

RUN apk update && apk add --no-cache python3 py3-pip
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY --from=builder /app/dist/*.whl ./
RUN pip install --no-cache-dir ./*.whl

EXPOSE 8080
ENTRYPOINT ["cdd-python", "server_json_rpc", "--listen", "0.0.0.0", "--port", "8080"]
