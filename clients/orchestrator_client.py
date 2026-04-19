import grpc
import grpc_stubs.orchestrator_pb2 as orchestrator_pb2
import grpc_stubs.orchestrator_pb2_grpc as orchestrator_pb2_grpc

from shared.tracing import init_tracing
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient

import random


init_tracing("orchestrator")
GrpcInstrumentorClient().instrument()

def run():
    
    channel = grpc.insecure_channel('localhost:50053')

    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

    request = orchestrator_pb2.BookingRequest(
        user_id="123",
        source="NYC",
        destination="LA"
    )

    response = stub.BookFlight(request)

    print("Booking Response:", response.message)

    # FOR STREAMING PRICES - UNCOMMENT TO TEST

    # responses = stub.StreamFlightPrices(request)

    # for flight in responses:
    #     print("Orchestrator Live Price:", flight.price)




if __name__ == "__main__":

    # SIMULATE MULTIPLE REQUESTS - UNCOMMENT TO TEST
    # requests = random.randint(20, 50)
    # for x in range (requests):
    #     run()

    run()