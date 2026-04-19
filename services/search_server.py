import grpc
from concurrent import futures

import grpc_stubs.search_pb2 as search_pb2
import grpc_stubs.search_pb2_grpc as search_pb2_grpc

import logging
import time
import random

from shared.tracing import init_tracing
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer

from prometheus_client import start_http_server
from shared.metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_LATENCY

start_http_server(8001)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchService(search_pb2_grpc.SearchServiceServicer):

    def SearchFlights(self, request, context):

        start_time = time.time()
        REQUEST_COUNT.labels(service="search", method="SearchFlights").inc()

        try:

            # SIMULATE RANDOM FAILURES TO TEST CIRCUIT BREAKER IN ORCHESTRATOR - UNCOMMENT TO TEST

            # if random.random() < 0.5:
            #     raise Exception("Search service failed randomly")
            
            logger.info(
                "Received SearchFlights request for source=%s destination=%s",
                request.source,
                request.destination,
            )

            flights = [
                search_pb2.Flight(flight_id="F1", airline="Delta", price=200.0),
                search_pb2.Flight(flight_id="F2", airline="United", price=250.0),
            ]

            return search_pb2.SearchResponse(flights=flights)

        except Exception as e:
            ERROR_COUNT.labels(service="search", method="SearchFlights").inc()
            raise

        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(service="search", method="SearchFlights").observe(duration)


    def StreamFlightPrices(self, request, context):
        start_time = time.time()

        REQUEST_COUNT.labels(service="search", method="StreamFlightPrices").inc()

        try:
            logger.info("Streaming flight prices")

            for i in range(5):
                price = random.uniform(180, 300)

                flight = search_pb2.Flight(
                    flight_id="F1",
                    airline="Delta",
                    price=price
                )

                yield flight

                time.sleep(1)

        except Exception as e:
            ERROR_COUNT.labels(service="search", method="StreamFlightPrices").inc()
            raise

        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(service="search", method="StreamFlightPrices").observe(duration)


def serve():

    init_tracing("search-service")

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

    search_pb2_grpc.add_SearchServiceServicer_to_server(SearchService(), server)

    server.add_secure_port('[::]:50052', server_credentials)

    server.start()
    logger.info("Search service running on port 50052")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
