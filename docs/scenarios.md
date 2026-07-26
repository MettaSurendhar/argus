# Demo Scenarios

Three fixed Kubernetes failure scenarios, each covering a distinct fault class. Argus is evaluated against these throughout `docs/manual_eval.md` and `docs/run_observation.md`.

## Scenario 1 — OOMKilled / CrashLoopBackOff

A container allocates memory in an unbounded loop, well past its configured limit, until the kernel kills it.

- YAML: [`data/demo_scenarios/scenario_1_oom.yaml`](../data/demo_scenarios/scenario_1_oom.yaml)
- Runbook: [`data/knowledge_base/oom_crashloop.md`](../data/knowledge_base/oom_crashloop.md)

```bash
kubectl apply -f data/demo_scenarios/scenario_1_oom.yaml
python -m instrumentation.main "why is this pod crashing" default my-oom-pod
```

## Scenario 2 — ImagePullBackOff

A pod references a container image tag that was never published.

- YAML: [`data/demo_scenarios/scenario_2_imagepull.yaml`](../data/demo_scenarios/scenario_2_imagepull.yaml)
- Runbook: [`data/knowledge_base/image_pull_backoff.md`](../data/knowledge_base/image_pull_backoff.md)

```bash
kubectl apply -f data/demo_scenarios/scenario_2_imagepull.yaml
python -m instrumentation.main "why won't this pod start" default my-badtag-pod
```

## Scenario 3 — Downstream service unreachable

A backend deployment is scaled to zero replicas, so a frontend pod's calls to it fail with connection-refused errors.

- YAML: [`data/demo_scenarios/scenario_3_service_unreachable.yaml`](../data/demo_scenarios/scenario_3_service_unreachable.yaml)
- Runbook: [`data/knowledge_base/service_unreachable.md`](../data/knowledge_base/service_unreachable.md)

```bash
kubectl apply -f data/demo_scenarios/scenario_3_service_unreachable.yaml
python -m instrumentation.main "why are requests failing" default my-frontend-pod
```

## Results

See [`docs/manual_eval.md`](manual_eval.md) for the scored summary across all three providers/models tested, and [`docs/run_observation.md`](run_observation.md) for the full raw terminal output backing those scores.
