# Raw Run Observations

Raw terminal output captured from actual `python -m src.main` runs, kept as
proof-of-run evidence backing the summarized ratings in `manual-eval.md`.

---

## Run Set 1 — Provider: `groq`, Model: `openai/gpt-oss-120b`

### Scenario 1: OOMKilled / CrashLoopBackOff

```
$ kubectl apply -f data/demo_scenarios/scenario_1_oom.yaml
pod/my-oom-pod created

$ python -m src.main "why is this pod crashing" default my-oom-pod
Loading weights: 100%|████████████████████████████████████| 103/103 [00:00<00:00, 461.13it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-oom-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-oom-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The pod is being killed by the kubelet due to exceeding its memory limit (50 Mi). The container runs a Python loop that allocates ~10 MiB repeatedly, quickly surpassing the limit, which results in an OOMKilled termination and a CrashLoopBackOff restart cycle.",
  "confidence": "high",
  "sources_used": [
    "oom_crashloop.md"
  ],
  "live_signals_used": [
    "container memory limit (50Mi) in pod spec",
    "memory-hog command that allocates memory",
    "absence of logs (indicates termination before start)"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The pod is being killed by the kubelet due to exceeding its memory limit (50 Mi). The container runs a Python loop that allocates ~10 MiB repeatedly, quickly surpassing the limit, which results in an OOMKilled termination and a CrashLoopBackOff restart cycle.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\"oom_crashloop.md\"],\n  \"live_signals_used\": [\"container memory limit (50Mi) in pod spec\", \"memory-hog command that allocates memory\", \"absence of logs (indicates termination before start)\"]\n}"
}
```

### Scenario 2: ImagePullBackOff

```
$ kubectl apply -f data/demo_scenarios/scenario_2_imagepull.yaml
pod/my-badtag-pod created

$ python -m src.main "why won't this pod start" default my-badtag-pod
Loading weights: 100%|████████████████████████████████████| 103/103 [00:00<00:00, 446.80it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-badtag-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-badtag-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The pod cannot start because the specified container image (nginx:v99-does-not-exist) does not exist, causing the kubelet to repeatedly fail pulling the image and the pod enters an ImagePullBackOff state.",
  "confidence": "high",
  "sources_used": [
    "image_pull_backoff.md"
  ],
  "live_signals_used": [
    "container image tag 'nginx:v99-does-not-exist' not found",
    "log: container \"bad-image\" is waiting to start: trying and failing to pull image"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The pod cannot start because the specified container image (nginx:v99-does-not-exist) does not exist, causing the kubelet to repeatedly fail pulling the image and the pod enters an ImagePullBackOff state.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\"image_pull_backoff.md\"],\n  \"live_signals_used\": [\"container image tag 'nginx:v99-does-not-exist' not found\", \"log: container \\\"bad-image\\\" is waiting to start: trying and failing to pull image\"]\n}"
}
```

### Scenario 3: Downstream service unreachable

```
$ kubectl apply -f data/demo_scenarios/scenario_3_service_unreachable.yaml
deployment.apps/my-backend created
service/my-backend-svc created
pod/my-frontend-pod created

$ python -m src.main "why are requests failing" default my-frontend-pod
Loading weights: 100%|████████████████████████████████████| 103/103 [00:00<00:00, 927.16it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-frontend-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-frontend-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The frontend pod cannot reach the downstream service because the service my-backend-svc is not listening on port 80 (or has no ready endpoints), resulting in connection-refused errors for every request.",
  "confidence": "high",
  "sources_used": [
    "service_unreachable.md"
  ],
  "live_signals_used": [
    "Recent logs showing connection refused to my-backend-svc:80",
    "Pod spec showing curl loop to http://my-backend-svc/"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The frontend pod cannot reach the downstream service because the service my-backend-svc is not listening on port 80 (or has no ready endpoints), resulting in connection-refused errors for every request.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\"service_unreachable.md\"],\n  \"live_signals_used\": [\"Recent logs showing connection refused to my-backend-svc:80\", \"Pod spec showing curl loop to http://my-backend-svc/\"]\n}"
}
```

---

## Run Set 2 — Provider: `openrouter`, Model: `meta-llama/llama-3.3-70b-instruct`

### Scenario 1: OOMKilled / CrashLoopBackOff

```
$ python -m src.main "why is this pod crashing" default my-oom-pod
Loading weights: 100%|███████████████████████████████████████████████████| 103/103 [00:00<00:00, 816.85it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-oom-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-oom-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The pod is crashing because it is running out of memory. The container is configured to request 20Mi of memory and has a limit of 50Mi, but the application is consuming more memory than the limit, causing it to be terminated with an OOMKilled status. The application code is intentionally growing its memory usage by 10MB at a time, which eventually exceeds the memory limit.",
  "confidence": "high",
  "sources_used": [
    "oom_crashloop.md"
  ],
  "live_signals_used": [
    "Live pod state",
    "Recent logs"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The pod is crashing because it is running out of memory. The container is configured to request 20Mi of memory and has a limit of 50Mi, but the application is consuming more memory than the limit, causing it to be terminated with an OOMKilled status. The application code is intentionally growing its memory usage by 10MB at a time, which eventually exceeds the memory limit.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\"oom_crashloop.md\"],\n  \"live_signals_used\": [\"Live pod state\", \"Recent logs\"]\n}"
}
```

### Scenario 2: ImagePullBackOff

```
$ python -m src.main "why won't this pod start" default my-badtag-pod
Loading weights: 100%|███████████████████████████████████████████████████| 103/103 [00:00<00:00, 920.56it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-badtag-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-badtag-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The pod won't start because it's unable to pull the specified Docker image, which likely does not exist or is not accessible. The image name 'nginx:v99-does-not-exist' suggests that this is an intentional test of an image pull failure.",
  "confidence": "high",
  "sources_used": [
    "image_pull_backoff.md"
  ],
  "live_signals_used": [
    "Live pod state",
    "Recent logs"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The pod won't start because it's unable to pull the specified Docker image, which likely does not exist or is not accessible. The image name 'nginx:v99-does-not-exist' suggests that this is an intentional test of an image pull failure.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\"image_pull_backoff.md\"],\n  \"live_signals_used\": [\"Live pod state\", \"Recent logs\"]\n}"
}
```

### Scenario 3: Downstream service unreachable

```
$ python -m src.main "why are requests failing" default my-frontend-pod
Loading weights: 100%|██████████████████████████████████████████████████| 103/103 [00:00<00:00, 1416.43it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-frontend-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-frontend-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The requests are failing because the frontend pod is unable to connect to the downstream backend service, indicated by repeated 'connection to backend failed' and 'Connection refused' errors in the logs. This suggests that the backend service is either not running, not listening on the expected port, or not properly configured to accept connections from the frontend pod.",
  "confidence": "high",
  "sources_used": [
    "service_unreachable.md"
  ],
  "live_signals_used": [
    "Recent logs",
    "Live pod state"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The requests are failing because the frontend pod is unable to connect to the downstream backend service, indicated by repeated 'connection to backend failed' and 'Connection refused' errors in the logs. This suggests that the backend service is either not running, not listening on the expected port, or not properly configured to accept connections from the frontend pod.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\"service_unreachable.md\"],\n  \"live_signals_used\": [\"Recent logs\", \"Live pod state\"]\n}"
}
```

---

## Run Set 3 — Provider: `groq`, Model: `openai/gpt-oss-20b`

### Scenario 1: OOMKilled / CrashLoopBackOff

```
$ python -m src.main "why is this pod crashing" default my-oom-pod
Loading weights: 100%|███████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1147.68it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-oom-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-oom-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The pod crashes because its container exceeds the 50Mi memory limit set in the pod spec. The Python script continuously allocates 10 MB bytearrays, quickly surpassing the limit and triggering Kubernetes to OOM-kill the container, which restarts in a CrashLoopBackOff cycle.",
  "confidence": "high",
  "sources_used": [
    "oom_crashloop.md"
  ],
  "live_signals_used": [
    "pod spec memory limits",
    "container code allocating 10 MB repeatedly"
  ],
  "raw_llm_output": "{\"hypothesis\":\"The pod crashes because its container exceeds the 50Mi memory limit set in the pod spec. The Python script continuously allocates 10 MB bytearrays, quickly surpassing the limit and triggering Kubernetes to OOM-kill the container, which restarts in a CrashLoopBackOff cycle.\",\"confidence\":\"high\",\"sources_used\":[\"oom_crashloop.md\"],\"live_signals_used\":[\"pod spec memory limits\",\"container code allocating 10 MB repeatedly\"]}"
}
```

### Scenario 2: ImagePullBackOff

```
$ python -m src.main "why won't this pod start" default my-badtag-pod
Loading weights: 100%|███████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1157.99it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-badtag-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-badtag-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The pod never reaches Running because the container image specified (nginx:v99-does-not-exist) cannot be pulled from the registry, causing Kubernetes to transition the pod into ImagePullBackOff / ErrImagePull. The log message \"image can't be pulled\" confirms the pull failure and the image tag does not exist or is inaccessible.",
  "confidence": "high",
  "sources_used": [
    "image_pull_backoff.md"
  ],
  "live_signals_used": [
    "pod status imagePullPolicy and container image field",
    "log message \"image can't be pulled\""
  ],
  "raw_llm_output": "{\"hypothesis\":\"The pod never reaches Running because the container image specified (nginx:v99-does-not-exist) cannot be pulled from the registry, causing Kubernetes to transition the pod into ImagePullBackOff / ErrImagePull. The log message \\\"image can't be pulled\\\" confirms the pull failure and the image tag does not exist or is inaccessible.\",\"confidence\":\"high\",\"sources_used\":[\"image_pull_backoff.md\"],\"live_signals_used\":[\"pod status imagePullPolicy and container image field\",\"log message \\\"image can't be pulled\\\"\"]}"
}
```

### Scenario 3: Downstream service unreachable

```
$ python -m src.main "why are requests failing" default my-frontend-pod
Loading weights: 100%|███████████████████████████████████████████████████████| 103/103 [00:00<00:00, 1499.20it/s]
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_get({'name': 'my-frontend-pod', 'namespace': 'default'})
[argus] tool call returned
[argus] spawning MCP server: ['kubernetes-mcp-server', '--read-only']
[argus] session opened, initializing...
[argus] initialized, calling tool: pods_log({'name': 'my-frontend-pod', 'namespace': 'default', 'tail': 50})
[argus] tool call returned
{
  "hypothesis": "The frontend pod is able to resolve the service IP (10.104.75.111) but every connection attempt to port 80 is refused. This indicates that the service selector does not match any running pod or the selected pod is not listening on port 80. As a result, downstream requests fail with connection refused errors.",
  "confidence": "high",
  "sources_used": [
    "service_unreachable.md",
    "live pod state",
    "recent logs"
  ],
  "live_signals_used": [
    "connection refused messages in logs",
    "pod status shows Running",
    "resolved IP for my-backend-svc"
  ],
  "raw_llm_output": "{\n  \"hypothesis\": \"The frontend pod is able to resolve the service IP (10.104.75.111) but every connection attempt to port 80 is refused. This indicates that the service selector does not match any running pod or the selected pod is not listening on port 80. As a result, downstream requests fail with connection refused errors.\",\n  \"confidence\": \"high\",\n  \"sources_used\": [\n    \"service_unreachable.md\",\n    \"live pod state\",\n    \"recent logs\"\n  ],\n  \"live_signals_used\": [\n    \"connection refused messages in logs\",\n   \"pod status shows Running\",\n    \"resolved IP for my-backend-svc\"\n  ]\n}"
}
```
