from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


def init_tracing(service_name: str):
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

    print(f"Tracing initialized for {service_name}")