from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import grpc
from concurrent import futures

import grpc_stubs.orchestrator_pb2 as orchestrator_pb2
import grpc_stubs.orchestrator_pb2_grpc as orchestrator_pb2_grpc

import grpc_stubs.user_pb2 as user_pb2
import grpc_stubs.user_pb2_grpc as user_pb2_grpc

import grpc_stubs.search_pb2 as search_pb2
import grpc_stubs.search_pb2_grpc as search_pb2_grpc

import logging
import time

from shared.tracing import init_tracing
from opentelemetry.instrumentation.grpc import (
    GrpcInstrumentorServer,
    GrpcInstrumentorClient
)

from opentelemetry import trace

from prometheus_client import start_http_server
from shared.metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_LATENCY

start_http_server(8002)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)
CERTS_DIR = PROJECT_ROOT / "certs"


class CircuitBreaker:

    def __init__(self, failure_threshold=3, recovery_time=10):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"

    def call(self, func, request):

        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time:
                logger.info("Circuit breaker moving to HALF_OPEN state")
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit is OPEN. Skipping call.")

        try:
            response = func(request)

            self.failure_count = 0
            self.state = "CLOSED"

            logger.info("Circuit breaker call succeeded; state=CLOSED")

            return response

        except Exception as e:
            if self.state != "HALF_OPEN":
                self.failure_count += 1

            self.last_failure_time = time.time()

            logger.warning("Circuit breaker failure count=%s", self.failure_count)

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning("Circuit breaker opened")

            raise


search_cb = CircuitBreaker()

def call_with_retry(func, request, max_retries=3):

    delay = 1  # start with 1 second

    for attempt in range(max_retries):

        try:
            return func(request)

        except Exception as e:
            logger.warning("Retry attempt %s failed: %s", attempt + 1, str(e))

            if attempt == max_retries - 1:
                raise

            time.sleep(delay)
            delay *= 2  # exponential backoff

def get_ssl_credentials():
    with open(CERTS_DIR / "client.key", "rb") as f:
        client_key = f.read()

    with open(CERTS_DIR / "client.crt", "rb") as f:
        client_cert = f.read()

    with open(CERTS_DIR / "ca.crt", "rb") as f:
        ca_cert = f.read()

    return grpc.ssl_channel_credentials(
        root_certificates=ca_cert,
        private_key=client_key,
        certificate_chain=client_cert
    )

def create_secure_channel(target):
    credentials = get_ssl_credentials()
    return grpc.secure_channel(target, credentials)


class OrchestratorService(orchestrator_pb2_grpc.OrchestratorServiceServicer):

    def BookFlight(self, request, context):

        start_time = time.time()

        REQUEST_COUNT.labels(service="orchestrator", method="BookFlight").inc()

        try:

            with tracer.start_as_current_span("Book Flight Business Logic"):

                user_id = request.user_id
                source = request.source
                destination = request.destination

                logger.info(
                    "Received BookFlight request for user_id=%s source=%s destination=%s",
                    user_id,
                    source,
                    destination,
                )

                user_channel = create_secure_channel('localhost:50051')
                user_stub = user_pb2_grpc.UserServiceStub(user_channel)

                user_request = user_pb2.UserRequest(user_id=user_id)

                with tracer.start_as_current_span("Validate User Logic") as span:
                    span.set_attribute("user_id", user_id)
                    span.set_attribute("source", source)
                    span.set_attribute("destination", destination)
                    user_response = call_with_retry(user_stub.ValidateUser, user_request)

                if not user_response.is_valid:
                    return orchestrator_pb2.BookingResponse(
                        success=False,
                        message="User is invalid"
                    )


                search_channel = create_secure_channel('localhost:50052')
                search_stub = search_pb2_grpc.SearchServiceStub(search_channel)

                search_request = search_pb2.SearchRequest(
                    source=source,
                    destination=destination
                )

                with tracer.start_as_current_span("Search Flights Logic") as span:
                    span.set_attribute("source", source)
                    span.set_attribute("destination", destination)
                    search_response = call_with_retry(
                        lambda req: search_cb.call(search_stub.SearchFlights, req),
                        search_request
                    )

                num_flights = len(search_response.flights)

                flight_lines = []
                for flight in search_response.flights:
                    flight_lines.append(f"  - {flight.flight_id}: ${flight.price} ({flight.airline})")

                message = f"{num_flights} flights found from {source} to {destination} for user {user_id}:\n" + "\n".join(flight_lines)

                return orchestrator_pb2.BookingResponse(success=True, message=message)
            
        except Exception as e:
            ERROR_COUNT.labels(service="orchestrator", method="BookFlight").inc()
            raise
        
        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(service="orchestrator", method="BookFlight").observe(duration)

    
    def StreamFlightPrices(self, request, context):

        start_time = time.time()

        REQUEST_COUNT.labels(service="orchestrator", method="StreamFlightPrices").inc()

        try:

            source = request.source
            destination = request.destination

            logger.info(
                "Streaming flight prices for source=%s destination=%s",
                source,
                destination,
            )

            # connect to search service
            search_channel = create_secure_channel('localhost:50052')
            search_stub = search_pb2_grpc.SearchServiceStub(search_channel)

            search_request = search_pb2.SearchRequest(
                source=source,
                destination=destination
            )


            responses = search_stub.StreamFlightPrices(search_request)


            with tracer.start_as_current_span("Streaming Prices Logic"):
                for flight in responses:
                    yield flight

        except Exception as e:
            ERROR_COUNT.labels(service="orchestrator", method="StreamFlightPrices").inc()
            raise
        
        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(service="orchestrator", method="StreamFlightPrices").observe(duration)


def serve():

    init_tracing("orchestrator")

    GrpcInstrumentorServer().instrument()   
    GrpcInstrumentorClient().instrument()   

    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    orchestrator_pb2_grpc.add_OrchestratorServiceServicer_to_server(
        OrchestratorService(), server
    )

    server.add_insecure_port('[::]:50053')

    server.start()
    logger.info("Orchestrator service running on port 50053")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
