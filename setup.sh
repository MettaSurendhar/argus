#!/bin/bash
# Runs directly on the host — NOT inside a container. Foundry and minikube
# both belong here; every failure during development happened when these
# were driven through a container's mounted docker socket instead of run
# directly, so this script deliberately doesn't do that.
set -e

banner() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

signoz_fully_ready() {
    curl -sf http://localhost:8080/api/v1/health > /dev/null 2>&1 || return 1
    local ch_status
    ch_status=$(docker inspect --format='{{.State.Health.Status}}' signoz-telemetrykeeper-clickhousekeeper-0 2>/dev/null || echo "missing")
    [ "$ch_status" = "healthy" ]
}

otlp_collector_ready() {
    # spans get sent here (gRPC, not HTTP — a plain TCP connect is enough
    # to confirm something's actually listening before we start exporting)
    (exec 3<>/dev/tcp/localhost/4317) 2>/dev/null
}

banner "Argus — setup"
echo "This script will, in order:"
echo "  1. Start (or reuse) a minikube cluster"
echo "  2. Deploy SigNoz via Foundry"
echo "  3. Build the agent's Docker image"
echo "  4. Build the RAG index"
echo "  5. Inject each of the 3 demo scenarios and run the agent against them"
echo ""
echo "Requires: minikube, kubectl, foundryctl, and docker already installed"
echo "on this host. See README.md 'Setup' if any of those are missing."
echo ""

# --- 1. minikube ---
banner "Step 1/5 — minikube"
if minikube status > /dev/null 2>&1; then
    echo "minikube already running, reusing it."
else
    echo "Starting minikube..."
    minikube start --driver=docker
fi
kubectl get nodes

# --- 2. SigNoz via Foundry ---
banner "Step 2/5 — deploying SigNoz via Foundry"
if signoz_fully_ready; then
    echo "SigNoz is already up and healthy (UI + Keeper both confirmed), skipping."
else
    echo "Running: foundryctl cast -f casting.yaml"
    foundryctl cast -f casting.yaml
    echo "Waiting for SigNoz to be fully ready (UI + Keeper both healthy)..."
    for i in $(seq 1 30); do
        if signoz_fully_ready; then
            echo "SigNoz is up."
            break
        fi
        sleep 5
    done
    if ! signoz_fully_ready; then
        echo ""
        echo "SigNoz didn't come up cleanly. This is a known, occasionally"
        echo "reproducible Foundry first-boot race (see README 'Known limitations')."
        echo "Try: docker rm -f signoz-telemetrykeeper-clickhousekeeper-0 && \\"
        echo "     docker volume rm signoz-telemetrykeeper-0-data && \\"
        echo "     foundryctl cast -f casting.yaml"
        echo "Then re-run this script, it'll skip straight past this step once healthy."
        exit 1
    fi
fi

# --- 3. Build the agent image ---
banner "Step 3/5 — building the agent's Docker image"
docker build -t argus .

# --- 4. Build the RAG index (persisted to ./chroma_db on the host) ---
banner "Step 4/5 — building the RAG index"
mkdir -p chroma_db
docker run --rm \
    -v "$(pwd)/chroma_db:/app/chroma_db" \
    --env-file .env \
    --entrypoint python \
    argus -m src.ingest.build_index

# --- 5. Inject scenarios and run the agent, one at a time ---
banner "Step 5/5 — running the 3 demo scenarios"

# Steps 2-4 can take 20+ minutes on a first run (plenty of warm-up time for
# SigNoz), or just seconds on a cached re-run — don't rely on elapsed time.
# Confirm the OTLP collector is actually accepting connections right before
# spans start flowing, so traces don't silently go missing on a fast run.
echo "Confirming SigNoz's OTLP collector is ready to receive traces..."
for i in $(seq 1 30); do
    if otlp_collector_ready; then
        echo "OTLP collector is up."
        break
    fi
    sleep 2
done
if ! otlp_collector_ready; then
    echo "Warning: OTLP collector on localhost:4317 isn't responding after"
    echo "60s. Scenarios will still run, but traces may not show up in"
    echo "SigNoz for this run — check docs/observations.md."
fi

run_agent() {
    # minikube's kubeconfig references cert files by absolute host path
    # (e.g. /home/<user>/.minikube/...), which won't exist inside the
    # container even with .minikube mounted at /root/.minikube — the path
    # in the file and the mount point don't match. Flattening embeds the
    # cert data directly into the kubeconfig (base64), sidestepping the
    # mismatch entirely.
    kubectl config view --minify --flatten > /tmp/argus-kubeconfig
    docker run --rm \
        --network host \
        -v "$(pwd)/chroma_db:/app/chroma_db" \
        -v "/tmp/argus-kubeconfig:/root/.kube/config:ro" \
        --env-file .env \
        --entrypoint python \
        argus -m instrumentation.main "$@"
}

echo ""
echo "--- Scenario 1: OOMKilled / CrashLoopBackOff ---"
echo "A container allocates memory in an unbounded loop past its 50Mi limit."
kubectl apply -f data/demo_scenarios/scenario_1_oom.yaml
echo "Waiting 30s for it to actually reach CrashLoopBackOff..."
sleep 30
run_agent "why is this pod crashing" default my-oom-pod

echo ""
echo "--- Scenario 2: ImagePullBackOff ---"
echo "A pod references an image tag that was never published."
kubectl apply -f data/demo_scenarios/scenario_2_imagepull.yaml
echo "Waiting 15s for the pull failure to register..."
sleep 15
run_agent "why won't this pod start" default my-badtag-pod

echo ""
echo "--- Scenario 3: Downstream service unreachable ---"
echo "A backend deployment is scaled to zero, so the frontend's calls to it fail."
kubectl apply -f data/demo_scenarios/scenario_3_service_unreachable.yaml
echo "Waiting 15s for the frontend's retry loop to hit the failure..."
sleep 15
run_agent "why are requests failing" default my-frontend-pod

banner "Done"
echo "All 3 scenarios ran. Open SigNoz at http://localhost:8080 and check:"
echo "  - Services tab, for the 'argus' service"
echo "  - Traces tab, filter service.name = argus, look for 'diagnose' spans"
echo "  - Dashboards tab, for the pre-built Argus dashboard (if imported)"
echo "  - Alerts tab, for the latency and silent-failure alert rules"
