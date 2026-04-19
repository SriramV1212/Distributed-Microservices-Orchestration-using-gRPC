from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import grpc
import grpc_stubs.search_pb2 as search_pb2
import grpc_stubs.search_pb2_grpc as search_pb2_grpc

CERTS_DIR = PROJECT_ROOT / "certs"


def get_ssl_credentials():
    with open(CERTS_DIR / "client.key", "rb") as f:
        client_key = f.read()

    with open(CERTS_DIR / "client.crt", "rb") as f:
        client_cert = f.read()

    with open(CERTS_DIR / "ca.crt", "rb") as f:
        ca_cert = f.read()

    return grpc.ssl_channel_credentials(
        root_certificates=ca_cert,
        private_key=client_key,
        certificate_chain=client_cert
    )

    
def run():
    channel = grpc.secure_channel('localhost:50052', get_ssl_credentials())

    stub = search_pb2_grpc.SearchServiceStub(channel)

    request = search_pb2.SearchRequest(source="NYC", destination="LA")

    stream_response = stub.StreamFlightPrices(request)


    for flight in stream_response:
        print("Live Price:", flight.price)


    search_response = stub.SearchFlights(request)

    for flight in search_response.flights:
        print("Search Result:", flight.flight_id, flight.airline, flight.price)


    


if __name__ == "__main__":
    run()
