from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import grpc
import grpc_stubs.user_pb2 as user_pb2
import grpc_stubs.user_pb2_grpc as user_pb2_grpc

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
    channel = grpc.secure_channel('localhost:50051', get_ssl_credentials())

    stub = user_pb2_grpc.UserServiceStub(channel)

    request = user_pb2.UserRequest(user_id="123")

    response = stub.ValidateUser(request)

    print("Response from server:", response.is_valid)


if __name__ == "__main__":
    run()
