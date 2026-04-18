import grpc
import orchestrator_pb2
import orchestrator_pb2_grpc

from tracing import init_tracing
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient


def run():
    init_tracing("orchestrator")
    GrpcInstrumentorClient().instrument()
    
    channel = grpc.insecure_channel('localhost:50053')

    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

    request = orchestrator_pb2.BookingRequest(
        user_id="123",
        source="NYC",
        destination="LA"
    )

    response = stub.BookFlight(request)

    print("Booking Response:", response.message)

    # for flight in responses:
    #     print("Orchestrator Live Price:", flight.price)




if __name__ == "__main__":
    run()