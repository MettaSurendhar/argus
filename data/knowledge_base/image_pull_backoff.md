# Runbook: ImagePullBackOff

## Symptoms
- `kubectl get pods` shows the pod stuck in `ImagePullBackOff` or `ErrImagePull`, never reaching `Running`.
- No containers actually start, so there are no application logs to check.

## How to confirm
1. Run `kubectl describe pod <name>` and look at the Events section near the bottom.
2. Look for a message like `Failed to pull image "<image>": ... not found` or `manifest unknown`.
3. Compare the exact image name and tag in the pod spec against what's actually published in the registry.

## Common causes
- A typo in the image tag (e.g. `v1.O` instead of `v1.0`, or a tag that was never pushed).
- The image was pushed to a different registry or repository than the one referenced in the deployment.
- Missing or expired registry credentials (`imagePullSecrets`), especially for private registries.

## Fix options
- Double check the exact tag against your CI/CD pipeline's actual output, don't rely on memory for what the "latest" tag should be.
- If it's a private registry, confirm the pod's `imagePullSecrets` reference a valid, non-expired secret.
- Consider a pre-deploy check that verifies the image tag exists in the registry before rolling out, to catch typos before they reach the cluster.
