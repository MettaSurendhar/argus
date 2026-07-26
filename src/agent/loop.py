"""
Agent orchestrator: ties retriever + tools + LLM together into one diagnose() call.
This is the ONLY place prompt-engineering logic should live.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.retriever.retrieve import retrieve
from src.tools.k8s_mcp import describe_pod, get_pod_logs
from src.config import call_llm

PROMPT_TEMPLATE = """You are an SRE assistant diagnosing a Kubernetes incident.

Use ONLY the runbook excerpts and live cluster state provided below.
Do not invent facts not present in the context.

Respond with ONLY a JSON object, no other text, in this exact shape:
{{
  "hypothesis": "<one paragraph root cause explanation>",
  "confidence": "<low|medium|high>",
  "sources_used": ["<runbook filename>", ...],
  "live_signals_used": ["<which live signals actually informed the answer>"]
}}

Question: {question}

Runbook excerpts:
{runbook_block}

Live pod state:
{live_state}

Recent logs:
{logs}
"""


def _strip_json_fences(text: str) -> str:
    """Free-tier models sometimes wrap JSON in ```json fences despite instructions."""
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text.strip()


def diagnose(user_question: str, namespace: str, pod_name: str, ablation: str = "full") -> dict:
    """
    ablation controls which inputs are actually included, for the ablation study:
    "baseline" -> neither runbooks nor live signals (LLM only sees the question)
    "rag_only" -> runbooks only
    "tools_only" -> live signals only
    "full" -> both (default / the real Argus design)
    """
    use_rag = ablation in ("rag_only", "full")
    use_tools = ablation in ("tools_only", "full")

    runbook_hits = retrieve(user_question, k=3) if use_rag else []
    live_state = describe_pod(namespace, pod_name) if use_tools else "(not provided for this condition)"
    logs = get_pod_logs(namespace, pod_name, tail=50) if use_tools else "(not provided for this condition)"

    runbook_block = (
        "\n".join(f"- [{h['source']}] {h['text'][:300]}" for h in runbook_hits)
        if runbook_hits else "(none provided for this condition)"
    )

    prompt = PROMPT_TEMPLATE.format(
        question=user_question,
        runbook_block=runbook_block,
        live_state=live_state,
        logs=logs,
    )

    raw = call_llm(prompt)
    cleaned = _strip_json_fences(raw)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Don't silently fail — surface the raw output so you can see what went wrong.
        parsed = {
            "hypothesis": "(failed to parse LLM output as JSON — see raw_llm_output)",
            "confidence": "low",
            "sources_used": [],
            "live_signals_used": [],
        }

    return {
        "hypothesis": parsed.get("hypothesis", ""),
        "confidence": parsed.get("confidence", "low"),
        "sources_used": parsed.get("sources_used", []),
        "live_signals_used": parsed.get("live_signals_used", []),
        "raw_llm_output": raw,
    }
