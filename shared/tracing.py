import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)
_TRACING_INITIALIZED = False


def init_tracing(service_name: str):
    global _TRACING_INITIALIZED

    if _TRACING_INITIALIZED:
        logger.info("Tracing already initialized for process")
        return

    resource = Resource(attributes={
        SERVICE_NAME: service_name
    })

    otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    insecure=True
    )

    span_processor = BatchSpanProcessor(otlp_exporter)

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)
    _TRACING_INITIALIZED = True

    logger.info("Tracing initialized for %s", service_name)
