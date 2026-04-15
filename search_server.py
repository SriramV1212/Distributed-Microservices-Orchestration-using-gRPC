import grpc
from concurrent import futures

import search_pb2
import search_pb2_grpc

import time
import random

class SearchService(search_pb2_grpc.SearchServiceServicer):

    def SearchFlights(self, request, context):

        if random.random() < 0.5:
          raise Exception("Search service failed randomly")
        
        print("Received search request for source:", request.source, "destination:", request.destination)

        source = request.source
        destination = request.destination

        flights = [
            search_pb2.Flight(flight_id="F1", airline="Delta", price=200.0),
            search_pb2.Flight(flight_id="F2", airline="United", price=250.0),
        ]

        return search_pb2.SearchResponse(flights=flights)


    def StreamFlightPrices(self, request, context):
        print("Streaming prices...")

        # simulate live updates
        for i in range(5):
            price = random.uniform(180, 300)

            flight = search_pb2.Flight(
                flight_id="F1",
                airline="Delta",
                price=price
            )

            yield flight   

            time.sleep(1)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    search_pb2_grpc.add_SearchServiceServicer_to_server(SearchService(), server)

    server.add_insecure_port('[::]:50052')

    server.start()
    print("Search Service running on port 50052...")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()