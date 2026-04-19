import grpc
from concurrent import futures

import grpc_stubs.user_pb2 as user_pb2
import grpc_stubs.user_pb2_grpc as user_pb2_grpc

from shared.tracing import init_tracing
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer

import logging
import time
from prometheus_client import start_http_server
from shared.metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_LATENCY

start_http_server(8000)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserService(user_pb2_grpc.UserServiceServicer):

    def ValidateUser(self, request, context):
        start_time = time.time()

        REQUEST_COUNT.labels(service="user", method="ValidateUser").inc()

        try:
            user_id = request.user_id
            logger.info("Received ValidateUser request for user_id=%s", user_id)

            if user_id == "123":
                response = user_pb2.UserResponse(is_valid=True)
            else:
                response = user_pb2.UserResponse(is_valid=False)

            return response

        except Exception as e:
            ERROR_COUNT.labels(service="user", method="ValidateUser").inc()
            raise

        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(service="user", method="ValidateUser").observe(duration)


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
    logger.info("User service running on port 50051")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
