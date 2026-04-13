import grpc
import orchestrator_pb2
import orchestrator_pb2_grpc


def run():
    channel = grpc.insecure_channel('localhost:50053')

    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

    request = orchestrator_pb2.BookingRequest(
        user_id="123",
        source="NYC",
        destination="LA"
    )

    responses = stub.StreamFlightPrices(request)

    for flight in responses:
        print("Orchestrator Live Price:", flight.price)


if __name__ == "__main__":
    run()