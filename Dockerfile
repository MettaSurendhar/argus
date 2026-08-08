FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# kubernetes-mcp-server: pinned version, matches what this project was
# actually tested against (see docs/run_observation.md)
RUN curl -L https://github.com/containers/kubernetes-mcp-server/releases/download/v0.0.65/kubernetes-mcp-server-linux-amd64 \
        -o /usr/local/bin/kubernetes-mcp-server \
    && chmod +x /usr/local/bin/kubernetes-mcp-server

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY instrumentation/ ./instrumentation/
COPY data/ ./data/

# no docker socket, no minikube, no foundry baked in here — this container
# only ever talks to a cluster and a SigNoz instance that already exist,
# both set up by setup.sh on the host. no fixed entrypoint since setup.sh
# needs to run two different things in it: the index build once, then the
# diagnose call per scenario.
