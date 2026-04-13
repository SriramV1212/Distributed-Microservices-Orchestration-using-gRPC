import grpc
from concurrent import futures

import user_pb2
import user_pb2_grpc


class UserService(user_pb2_grpc.UserServiceServicer):

    def ValidateUser(self, request, context):
        user_id = request.user_id
        print("Received request for user_id:", user_id)

        if user_id == "123":
            return user_pb2.UserResponse(is_valid=True)
        else:
            return user_pb2.UserResponse(is_valid=False)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)

    server.add_insecure_port('[::]:50051')

    server.start()
    print("Server is running on port 50051...")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()