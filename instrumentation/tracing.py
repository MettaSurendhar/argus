"""
sets up the otel tracer once at import time. everything else in this repo
just does `from instrumentation.tracing import tracer` and starts spans,
no one else needs to touch exporters/providers directly.
"""
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from instrumentation.config import OTLP_ENDPOINT, SERVICE_NAME

resource = Resource.create({"service.name": SERVICE_NAME})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("argus.instrumented_agent")


def flush():
    """call this before the process exits, otherwise the last batch of
    spans can get dropped since BatchSpanProcessor exports on a timer,
    not immediately per-span"""
    provider.force_flush()
