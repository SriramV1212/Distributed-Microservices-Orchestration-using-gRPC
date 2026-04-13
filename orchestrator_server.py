import grpc
from concurrent import futures

import orchestrator_pb2
import orchestrator_pb2_grpc

import user_pb2
import user_pb2_grpc

import search_pb2
import search_pb2_grpc


class OrchestratorService(orchestrator_pb2_grpc.OrchestratorServiceServicer):

    def BookFlight(self, request, context):

        user_id = request.user_id
        source = request.source
        destination = request.destination

        print("Orchestrator received request")

        # STEP 1: call User Service
        user_channel = grpc.insecure_channel('localhost:50051')
        user_stub = user_pb2_grpc.UserServiceStub(user_channel)

        user_request = user_pb2.UserRequest(user_id=user_id)
        user_response = user_stub.ValidateUser(user_request)

        if not user_response.is_valid:
            return orchestrator_pb2.BookingResponse(
                success=False,
                message="User is invalid"
            )

        # STEP 2: call Search Service
        search_channel = grpc.insecure_channel('localhost:50052')
        search_stub = search_pb2_grpc.SearchServiceStub(search_channel)

        search_request = search_pb2.SearchRequest(
            source=source,
            destination=destination
        )

        search_response = search_stub.SearchFlights(search_request)

        # STEP 3: combine result
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
        search_channel = grpc.insecure_channel('localhost:50052')
        search_stub = search_pb2_grpc.SearchServiceStub(search_channel)

        search_request = search_pb2.SearchRequest(
            source=source,
            destination=destination
        )

        responses = search_stub.StreamFlightPrices(search_request)

  
        for flight in responses:
            yield flight


def serve():
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