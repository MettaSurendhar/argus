"""
settings for the observability layer. now that argus and its instrumentation
live in the same repo, this is just otel/signoz config, no more cross-repo
path juggling.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# signoz's otel collector, exposed by foundry's default compose setup
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

SERVICE_NAME = "argus"
