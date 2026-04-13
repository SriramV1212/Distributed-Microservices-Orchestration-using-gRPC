import grpc
import search_pb2
import search_pb2_grpc


def run():
    channel = grpc.insecure_channel('localhost:50052')

    stub = search_pb2_grpc.SearchServiceStub(channel)

    request = search_pb2.SearchRequest(source="NYC", destination="LA")

    responses = stub.StreamFlightPrices(request)

    for flight in responses:
        print("Live Price:", flight.price)


if __name__ == "__main__":
    run()