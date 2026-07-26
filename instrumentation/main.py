"""
same cli shape as argus's own src/main.py, just calling the instrumented
diagnose() and making sure spans get flushed before the process exits.

usage:
    python -m instrumentation.main "why is this pod crashing" default my-oom-pod
"""
import argparse
import json

from instrumentation.instrumented_agent import diagnose
from instrumentation.tracing import flush


def main():
    parser = argparse.ArgumentParser(description="Argus, instrumented with OTel spans for SigNoz")
    parser.add_argument("question")
    parser.add_argument("namespace")
    parser.add_argument("pod_name")
    parser.add_argument("--ablation", choices=["baseline", "rag_only", "tools_only", "full"], default="full")
    args = parser.parse_args()

    try:
        result = diagnose(args.question, args.namespace, args.pod_name, ablation=args.ablation)
        print(json.dumps(result, indent=2))
    finally:
        # batchspanprocessor exports on a timer, without this the last
        # run's spans can just get dropped when the process exits
        flush()


if __name__ == "__main__":
    main()
