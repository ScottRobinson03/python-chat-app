import errno
import socket
import sys
import typing
import traceback

from src.backend.constants import HEADER_LENGTH
from src.backend.server import Server

if typing.TYPE_CHECKING:
    from src.gui.__main__ import MainWindow


IP = "127.0.0.1"
PORT = 5001


class Client:
    def __init__(self, username: str, app: "MainWindow"):
        self.username = username.encode()
        self.app = app

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((IP, PORT))
        self.client_socket.setblocking(False)

        username_header = Server.generate_message_header(self.username)
        self.client_socket.send(username_header + self.username)

    def listen(self):
        while True:
            try:
                while True:
                    timestamp_header = self.client_socket.recv(HEADER_LENGTH)
                    if not len(timestamp_header):
                        print("WARNING: Connection closed by the server.")
                        sys.exit()
                    timestamp_length = int(timestamp_header.decode())
                    timestamp = int(self.client_socket.recv(timestamp_length).decode())

                    author_header = self.client_socket.recv(HEADER_LENGTH)
                    # if not len(username_header):
                    #     print("WARNING: Connection closed by the server.")
                    #     sys.exit()
                    username_length = int(author_header.decode())
                    author = self.client_socket.recv(username_length).decode()

                    message_header = self.client_socket.recv(HEADER_LENGTH)
                    message_length = int(message_header.decode())
                    message = self.client_socket.recv(message_length).decode()

                    self.app.message_signal.emit(
                        timestamp,
                        author,
                        message,
                    )

            except IOError as e:
                if e.errno not in {errno.EAGAIN, errno.EWOULDBLOCK}:
                    print("Unexpected Reading Error:")
                    traceback.print_exception(e)
                    sys.exit(1)
                continue

            except Exception as e:
                print("Unexpected General Error:")
                traceback.print_exception(e)
                sys.exit(1)
