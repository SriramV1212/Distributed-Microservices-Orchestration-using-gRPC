from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "grpc_requests_total",
    "Total gRPC requests",
    ["service", "method"]
)

ERROR_COUNT = Counter(
    "grpc_errors_total",
    "Total gRPC errors",
    ["service", "method"]
)

REQUEST_LATENCY = Histogram(
    "grpc_request_latency_seconds",
    "Latency of gRPC requests",
    ["service", "method"]
)