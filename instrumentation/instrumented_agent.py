"""
same diagnose() logic as argus's src/agent/loop.py, wrapped in otel spans at
each of the three seams: retrieval, mcp tool calls, and the llm call.

kept as its own copy instead of monkeypatching src/agent/loop.py directly,
so the plain (non-instrumented) CLI in src/main.py still works untouched
for quick manual testing without needing signoz running.
"""
import json

from instrumentation.tracing import tracer
from src.retriever.retrieve import retrieve
from src.tools.k8s_mcp import describe_pod, get_pod_logs
from src.config import call_llm
from src.agent.loop import PROMPT_TEMPLATE, _strip_json_fences


def diagnose(user_question: str, namespace: str, pod_name: str, ablation: str = "full") -> dict:
    with tracer.start_as_current_span("diagnose") as root_span:
        root_span.set_attribute("argus.question", user_question)
        root_span.set_attribute("argus.namespace", namespace)
        root_span.set_attribute("argus.pod_name", pod_name)
        root_span.set_attribute("argus.ablation", ablation)

        use_rag = ablation in ("rag_only", "full")
        use_tools = ablation in ("tools_only", "full")

        with tracer.start_as_current_span("retrieve_runbooks") as span:
            runbook_hits = retrieve(user_question, k=3) if use_rag else []
            span.set_attribute("argus.hits_returned", len(runbook_hits))
            if runbook_hits:
                span.set_attribute("argus.sources", [h["source"] for h in runbook_hits])

        with tracer.start_as_current_span("k8s_describe_pod") as span:
            live_state = describe_pod(namespace, pod_name) if use_tools else "(not provided for this condition)"
            span.set_attribute("argus.response_length", len(live_state))

        with tracer.start_as_current_span("k8s_get_logs") as span:
            logs = get_pod_logs(namespace, pod_name, tail=50) if use_tools else "(not provided for this condition)"
            span.set_attribute("argus.response_length", len(logs))

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

        with tracer.start_as_current_span("llm_call") as span:
            raw = call_llm(prompt)
            span.set_attribute("argus.prompt_length", len(prompt))
            span.set_attribute("argus.response_length", len(raw))

        cleaned = _strip_json_fences(raw)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = {
                "hypothesis": "(failed to parse LLM output as JSON, see raw_llm_output)",
                "confidence": "low",
                "sources_used": [],
                "live_signals_used": [],
            }
            root_span.set_attribute("argus.parse_failed", True)

        root_span.set_attribute("argus.confidence", parsed.get("confidence", "low"))

        return {
            "hypothesis": parsed.get("hypothesis", ""),
            "confidence": parsed.get("confidence", "low"),
            "sources_used": parsed.get("sources_used", []),
            "live_signals_used": parsed.get("live_signals_used", []),
            "raw_llm_output": raw,
        }
