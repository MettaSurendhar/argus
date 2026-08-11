# Usage — what to do after `setup.sh`

`setup.sh` only runs the 3 fixed demo scenarios automatically. This page
covers what you'd do next by hand:

- Asking your own questions
- Running against a pod you set up yourself
- Building the SigNoz dashboard + alerts (neither auto-created — no
  dashboard/alert JSON checked into this repo, you build them once in
  the UI)

---

- [1. Asking questions](#1-asking-questions)
- [2. All the cases](#2-all-the-cases)
- [3. Building the dashboard](#3-building-the-dashboard)
- [4. Building the alerts](#4-building-the-alerts)

---

## 1. Asking questions

Two ways to run `diagnose()` against a pod — pick whichever matches your
setup.

**Via Docker** (matches exactly what `setup.sh` runs, no local Python env
needed). minikube's kubeconfig needs flattening first — same reason
`setup.sh`'s `run_agent()` does this, see
[`docs/observations.md`](observations.md#5-step-55-fails-mcp-server-cant-read-minikube-certs-inside-container):

```bash
kubectl config view --minify --flatten > /tmp/argus-kubeconfig
docker run --rm --network host \
    -v "$(pwd)/chroma_db:/app/chroma_db" \
    -v "/tmp/argus-kubeconfig:/root/.kube/config:ro" \
    --env-file .env --entrypoint python \
    argus -m instrumentation.main "<your question>" <namespace> <pod-name>
```

**Via a local Python env** (one-time venv setup: README's
["Running things by hand"](../README.md#running-things-by-hand)):

```bash
python -m instrumentation.main "why is this pod failing" default my-pod
```

- Both produce the same JSON on stdout (`hypothesis`, `confidence`,
  `sources_used`, `live_signals_used`, `raw_llm_output`)
- Both export the same trace to SigNoz
- Only difference: Docker vs your local Python interpreter running it

**Ablation flag** — compare what each input source contributes (backs
the study in `docs/manual_eval.md`):

```bash
python -m instrumentation.main "<question>" <namespace> <pod> --ablation rag_only
# baseline | rag_only | tools_only | full (default)
```

## 2. All the cases

**The 3 built-in scenarios** (what `setup.sh` runs) — YAML + exact
command for each in [`docs/scenarios.md`](scenarios.md):

1. OOMKilled / CrashLoopBackOff
2. ImagePullBackOff
3. Downstream service unreachable

**Your own pod, any question** — Argus doesn't care whether the pod
matches a known runbook:

```bash
kubectl apply -f my-broken-pod.yaml
python -m instrumentation.main "why is this pod stuck pending" default my-broken-pod
```

- No match in `data/knowledge_base/`? Expect `sources_used: []` and a
  lower-confidence answer built only from live signals
- That's expected, not a bug — see the RAG-vs-tools ablation results in
  `docs/manual_eval.md` for how much each source actually matters

**Re-running a scenario** — pod's already applied, just re-ask:

```bash
python -m instrumentation.main "why is this pod crashing" default my-oom-pod
```

**Adding a new runbook** — drop a `.md` file in `data/knowledge_base/`,
then rebuild the index:

```bash
python -m src.ingest.build_index
```

## 3. Building the dashboard

- Dashboards build from spans Argus already exports
- No special setup beyond running at least one question first (so
  there's data for the query builder to find)

Open `http://localhost:8080` → **Dashboards** → **+ New Dashboard** → add
4 panels:

### Panel 1 — Latency by pipeline stage

Avg duration per span, grouped by span name — fastest way to see where
time is going in a `diagnose()` call.

- **Panel type:** Bar chart (or Table)
- **Data source:** Traces
- **Aggregation:** Avg of `Duration`
- **Filter:** `service.name = argus`
- **Group by:** `name` (shows `retrieve_runbooks`, `k8s_describe_pod`,
  `k8s_get_logs`, `llm_call` as separate bars)

### Panel 2 — `diagnose` (root span) latency trend

p95 latency of the whole request over time — for catching regressions,
not one-off noise.

- **Panel type:** Time series
- **Data source:** Traces
- **Aggregation:** P95 of `Duration`
- **Filter:** `service.name = argus` AND `name = diagnose`

### Panel 3 — Call volume

Count of spans by name — sanity check for whether requests complete the
full pipeline (if `llm_call`'s count is consistently lower than
`diagnose`'s, something's failing partway through — see Alert 2, which
formalizes this exact check).

- **Panel type:** Time series or Bar chart
- **Data source:** Traces
- **Aggregation:** Count
- **Filter:** `service.name = argus`
- **Group by:** `name`

### Panel 4 — Confidence distribution

Breakdown of the agent's self-reported confidence across runs, from the
`argus.confidence` attribute on the root span.

- **Panel type:** Pie chart (or Bar chart)
- **Data source:** Traces
- **Aggregation:** Count
- **Filter:** `service.name = argus` AND `name = diagnose`
- **Group by:** `argus.confidence` (attribute)

Save the dashboard once all 4 panels are added, then screenshot per
[`docs/screenshots/README.md`](screenshots/README.md).

## 4. Building the alerts

Open `http://localhost:8080` → **Alerts** → **+ New Alert Rule**.

### Alert 1 — Argus diagnose latency high

Fires when the agent gets suspiciously slow.

- **Alert type:** Metric-based on Traces
- **Query:** P95 of `Duration`, filter `service.name = argus` AND
  `name = diagnose`
- **Condition:** above threshold (a bit above your normal p95 from
  Panel 2 — e.g. 2x typical `diagnose` latency)
- **Evaluation window:** 5 minutes
- **Notification channel:** whatever's configured (email/Slack/webhook)

### Alert 2 — Argus silent failure (diagnose incomplete)

Fires when runs start but never reach the LLM step — `diagnose` span
count exceeds `llm_call` span count in the same window, meaning the
pipeline dies partway through without raising a visible error.

- **Alert type:** Metric-based on Traces (needs two queries combined —
  check SigNoz's query builder for a formula/expression option to
  compute `count(diagnose) - count(llm_call)`)
- **Condition:** result > 0
- **Evaluation window:** 5 minutes
- **Notification channel:** same as above

This alert exists because of what Panel 3 (call volume) would otherwise
require noticing manually — turns "eyeball the dashboard for a gap" into
an actual page.

Screenshot both rules, plus one triggered notification if you can force
one (e.g. temporarily set an absurdly low latency threshold on Alert 1
and run a scenario), per [`docs/screenshots/README.md`](screenshots/README.md).
