"""
CLI entrypoint.

Usage:
    python -m src.main "why is this pod crashing" default my-oom-pod
    python -m src.main "why is this pod crashing" default my-oom-pod --ablation rag_only
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.agent.loop import diagnose


def main():
    parser = argparse.ArgumentParser(description="Argus: RAG + MCP incident diagnosis agent")
    parser.add_argument("question", help="The question to ask, e.g. 'why is this pod crashing'")
    parser.add_argument("namespace", help="Kubernetes namespace")
    parser.add_argument("pod_name", help="Pod name")
    parser.add_argument(
        "--ablation",
        choices=["baseline", "rag_only", "tools_only", "full"],
        default="full",
        help="Which inputs to enable, for the ablation study (default: full)",
    )
    args = parser.parse_args()

    result = diagnose(args.question, args.namespace, args.pod_name, ablation=args.ablation)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
