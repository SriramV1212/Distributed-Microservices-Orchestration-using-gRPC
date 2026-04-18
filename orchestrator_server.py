import grpc
from concurrent import futures

import orchestrator_pb2
import orchestrator_pb2_grpc

import user_pb2
import user_pb2_grpc

import search_pb2
import search_pb2_grpc

import time

from tracing import init_tracing
from opentelemetry.instrumentation.grpc import (
    GrpcInstrumentorServer,
    GrpcInstrumentorClient
)

from opentelemetry import trace

tracer = trace.get_tracer(__name__)


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
                print("Trying half-open state...")
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit is OPEN. Skipping call.")

        try:
            response = func(request)

            self.failure_count = 0
            self.state = "CLOSED"

            print("Circuit is CLOSED. Call successful.")

            return response

        except Exception as e:
            if self.state != "HALF_OPEN":
                self.failure_count += 1

            self.last_failure_time = time.time()

            print(f"Circuit failure count: {self.failure_count}")

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                print("Circuit OPENED!")

            raise e


search_cb = CircuitBreaker()

def call_with_retry(func, request, max_retries=3):

    delay = 1  # start with 1 second

    for attempt in range(max_retries):

        try:
            return func(request)

        except Exception as e:
            print(f"Attempt {attempt+1} failed: {str(e)}")

            if attempt == max_retries - 1:
                raise e

            time.sleep(delay)
            delay *= 2  # exponential backoff

def get_ssl_credentials():
    with open("certs/client.key", "rb") as f:
        client_key = f.read()

    with open("certs/client.crt", "rb") as f:
        client_cert = f.read()

    with open("certs/ca.crt", "rb") as f:
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

        with tracer.start_as_current_span("Book Flight Business Logic"):

            user_id = request.user_id
            source = request.source
            destination = request.destination

            print("Orchestrator received request")

            user_channel = create_secure_channel('localhost:50051')
            user_stub = user_pb2_grpc.UserServiceStub(user_channel)

            user_request = user_pb2.UserRequest(user_id=user_id)

            with tracer.start_as_current_span("Validate User Logic") as span:
                span.set_attribute("user_id", user_id)
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

            return orchestrator_pb2.BookingResponse(
                success=True,
                message=f"{num_flights} flights found"
            )
    
    def StreamFlightPrices(self, request, context):



        source = request.source
        destination = request.destination

        print("Orchestrator streaming prices...")

        # connect to search service
        search_channel = create_secure_channel('localhost:50052')
        search_stub = search_pb2_grpc.SearchServiceStub(search_channel)

        search_request = search_pb2.SearchRequest(
            source=source,
            destination=destination
        )


        responses = search_stub.StreamFlightPrices(search_request)


        for flight in responses:
            yield flight


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
    print("Orchestrator running on port 50053...")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()