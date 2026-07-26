# Runbook: Downstream Service Unreachable

## Symptoms
- The pod itself is `Running`, but the application logs show connection errors, timeouts, or refused connections to another internal service.
- Requests that depend on the downstream service fail or time out; requests that don't depend on it succeed normally.

## How to confirm
1. Check the application logs for the specific error (e.g. `connection refused`, `no route to host`, `dial tcp: i/o timeout`).
2. Run `kubectl get endpoints <service-name>` for the downstream service, if it shows no addresses, there are no healthy pods behind it.
3. Run `kubectl get deployment <downstream-name>` and check the replica count, a deployment scaled to 0 replicas will have no backing pods at all.
4. Check the Service spec's `port` and `targetPort` values against what the downstream container actually listens on, a mismatch here causes connection refusals even with healthy pods.

## Common causes
- The downstream service was scaled to 0 replicas (intentionally or by mistake) and never scaled back up.
- A Service's `targetPort` doesn't match the port the container actually exposes.
- A NetworkPolicy or namespace boundary silently blocking traffic between the two pods.

## Fix options
- If replicas are at 0, scale back up and investigate why they were scaled down in the first place.
- If it's a port mismatch, fix the Service spec's `targetPort` to match the container's actual listening port.
- Add a synthetic health check that specifically exercises the cross-service call path, not just each service's own liveness probe, so this class of failure is caught proactively.
