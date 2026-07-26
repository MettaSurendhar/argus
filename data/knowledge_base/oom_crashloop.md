# Runbook: OOMKilled / CrashLoopBackOff

## Symptoms
- `kubectl get pods` shows the pod cycling through `CrashLoopBackOff`.
- `kubectl describe pod <name>` shows `Last State: Terminated`, `Reason: OOMKilled`.
- Restart count keeps climbing every few minutes.

## How to confirm
1. Run `kubectl describe pod <name>` and check the `Last State` section for `Reason: OOMKilled`.
2. Compare the container's actual memory usage (via `kubectl top pod <name>`, if metrics-server is installed) against the `resources.limits.memory` set in the pod spec.
3. Check application logs just before the crash for signs of unbounded memory growth (e.g. a cache that never evicts, a memory leak in a long-running loop).

## Common causes
- The memory limit was set too low for what the workload actually needs under real load.
- A memory leak in the application itself, where usage climbs over time regardless of the limit.
- A sudden spike in traffic or batch size that pushes usage past the limit briefly.

## Fix options
- If the limit is simply too conservative, raise `resources.limits.memory` to a value based on observed peak usage plus headroom.
- If usage climbs unbounded over time, that's a leak, not a sizing problem, raising the limit only delays the crash.
- Add a memory-usage alert well before the limit is hit, so this is caught before it becomes a customer-facing incident.
