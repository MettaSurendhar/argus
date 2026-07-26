"""
K8s tool client. Two backends, selected via TOOL_DATA_SOURCE env var:
- "live": calls a running K8s MCP server (containers/kubernetes-mcp-server) over stdio.
- "snapshot": reads from a downloaded ITBench-Lite scenario folder instead of a
  live cluster. Used for the paper's evaluation dataset.

Both modes return the exact same shapes (see ARCHITECTURE.md section 4.2) so
src/agent/loop.py never needs to know which one is active.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import TOOL_DATA_SOURCE

SNAPSHOT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "data", "itbench_snapshots")

# ---- Configure this once you've installed the native binary ----
# containers/kubernetes-mcp-server: a Go-native binary, talks directly to the
# K8s API (no kubectl shelling out), genuinely supports --read-only as a real flag.
MCP_SERVER_COMMAND = ["kubernetes-mcp-server", "--read-only"]
MCP_SERVER_ENV = {}


def describe_pod(namespace: str, pod_name: str) -> str:
    if TOOL_DATA_SOURCE == "snapshot":
        return _snapshot_describe_pod(namespace, pod_name)
    return _live_describe_pod(namespace, pod_name)


def get_pod_logs(namespace: str, pod_name: str, tail: int = 50) -> str:
    if TOOL_DATA_SOURCE == "snapshot":
        return _snapshot_get_logs(namespace, pod_name, tail)
    return _live_get_logs(namespace, pod_name, tail)


def list_pods(namespace: str) -> list[dict]:
    if TOOL_DATA_SOURCE == "snapshot":
        return _snapshot_list_pods(namespace)
    return _live_list_pods(namespace)


# ---------------------------------------------------------------------------
# LIVE mode: talks to a real MCP server over stdio.
# Requires: pip install mcp, and the MCP_SERVER_COMMAND binary installed/available.
# ---------------------------------------------------------------------------

def _call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Opens a fresh stdio connection, calls one tool, closes it.
    NOTE: for a CLI tool that makes several calls per run (as diagnose() does),
    this reconnects each time. Fine for a demo-sized v1 — if it's too slow,
    refactor to hold one session open for the whole diagnose() call instead.
    """
    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def _run():
        server_params = StdioServerParameters(
            command=MCP_SERVER_COMMAND[0],
            args=MCP_SERVER_COMMAND[1:],
            env={**os.environ, **MCP_SERVER_ENV},
        )
        print(f"[argus] spawning MCP server: {MCP_SERVER_COMMAND}", file=sys.stderr)
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("[argus] session opened, initializing...", file=sys.stderr)
                await asyncio.wait_for(session.initialize(), timeout=20)
                print(f"[argus] initialized, calling tool: {tool_name}({arguments})", file=sys.stderr)
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments=arguments), timeout=30
                )
                print("[argus] tool call returned", file=sys.stderr)
                texts = [c.text for c in result.content if hasattr(c, "text")]
                return "\n".join(texts)

    try:
        return asyncio.run(_run())
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"MCP call to '{tool_name}' timed out. Check: (1) does `kubectl describe pod` "
            f"work directly in this same terminal? (2) does the MCP inspector reach this "
            f"tool successfully outside of Argus?"
        )


def _live_describe_pod(namespace: str, pod_name: str) -> str:
    raw = _call_mcp_tool("pods_get", {
        "name": pod_name,
        "namespace": namespace,
    })
    return raw[:2000]


def _live_get_logs(namespace: str, pod_name: str, tail: int) -> str:
    return _call_mcp_tool("pods_log", {
        "name": pod_name,
        "namespace": namespace,
        "tail": tail,
    })


def _live_list_pods(namespace: str) -> list[dict]:
    raw = _call_mcp_tool("pods_list_in_namespace", {"namespace": namespace})
    return [{"name": "unparsed", "status": "see raw", "restarts": 0, "raw": raw[:500]}]


# ---------------------------------------------------------------------------
# SNAPSHOT mode: reads from an ITBench-Lite scenario folder on disk.
# ---------------------------------------------------------------------------

CURRENT_SNAPSHOT_SCENARIO = os.environ.get("ITBENCH_SCENARIO_ID", "")


def _scenario_path(*parts) -> str:
    if not CURRENT_SNAPSHOT_SCENARIO:
        raise RuntimeError(
            "TOOL_DATA_SOURCE=snapshot but no scenario selected. "
            "Set ITBENCH_SCENARIO_ID to a folder name under data/itbench_snapshots/."
        )
    return os.path.join(SNAPSHOT_ROOT, CURRENT_SNAPSHOT_SCENARIO, *parts)


def _read_tsv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _snapshot_list_pods(namespace: str) -> list[dict]:
    rows = _read_tsv(_scenario_path("k8s_objects_raw.tsv"))
    pods = [r for r in rows if r.get("kind", "").lower() == "pod" and r.get("namespace") == namespace]
    return [
        {"name": r.get("name", ""), "status": r.get("status", "unknown"), "restarts": int(r.get("restarts", 0) or 0)}
        for r in pods
    ]


def _snapshot_describe_pod(namespace: str, pod_name: str) -> str:
    rows = _read_tsv(_scenario_path("k8s_objects_raw.tsv"))
    events = _read_tsv(_scenario_path("k8s_events_raw.tsv"))
    pod_row = next((r for r in rows if r.get("name") == pod_name), None)
    pod_events = [e for e in events if e.get("involved_object_name") == pod_name]
    lines = [f"Pod: {pod_name}", f"Namespace: {namespace}"]
    if pod_row:
        lines.append(f"Status: {pod_row.get('status', 'unknown')}")
    for e in pod_events[:20]:
        lines.append(f"Event: {e.get('reason', '')} - {e.get('message', '')}")
    return "\n".join(lines)[:2000]


def _snapshot_get_logs(namespace: str, pod_name: str, tail: int) -> str:
    log_path = _scenario_path("logs", f"{pod_name}.log")
    if not os.path.exists(log_path):
        return f"(no captured logs found for {pod_name} in this snapshot)"
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    return "".join(lines[-tail:])
