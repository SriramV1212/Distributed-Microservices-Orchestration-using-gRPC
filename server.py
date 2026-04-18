import grpc
from concurrent import futures

import user_pb2
import user_pb2_grpc

from tracing import init_tracing
from opentelemetry.instrumentation.grpc import (
    GrpcInstrumentorServer,
    GrpcInstrumentorClient
)


class UserService(user_pb2_grpc.UserServiceServicer):

    def ValidateUser(self, request, context):
        user_id = request.user_id
        print("Received request for user_id:", user_id)

        if user_id == "123":
            return user_pb2.UserResponse(is_valid=True)
        else:
            return user_pb2.UserResponse(is_valid=False)


def serve():
    init_tracing("user-service")

    GrpcInstrumentorServer().instrument()

    with open("certs/server.key", "rb") as f:
        private_key = f.read()

    with open("certs/server.crt", "rb") as f:
        certificate_chain = f.read()

    with open("certs/ca.crt", "rb") as f:
        ca_cert = f.read()

    server_credentials = grpc.ssl_server_credentials(
    [(private_key, certificate_chain)],
    root_certificates=ca_cert,
    require_client_auth=True
    )


    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)

    server.add_secure_port('[::]:50051', server_credentials)

    server.start()
    print("Server is running on port 50051...")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()