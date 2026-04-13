import grpc
import user_pb2
import user_pb2_grpc


def run():
    channel = grpc.insecure_channel('localhost:50051')

    stub = user_pb2_grpc.UserServiceStub(channel)

    request = user_pb2.UserRequest(user_id="123")

    response = stub.ValidateUser(request)

    print("Response from server:", response.is_valid)


if __name__ == "__main__":
    run()