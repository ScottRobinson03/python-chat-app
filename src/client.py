import errno
import socket
import sys
import threading
import traceback

from src.constants import HEADER_LENGTH

IP = "127.0.0.1"
PORT = 5001


class KeyboardThread(threading.Thread):
    def __init__(self, client_socket: socket.socket):
        super().__init__(daemon=True, name="KeyboardThread")
        self.client_socket = client_socket
        self.username = None
        self.start()

    def run(self):
        while True:
            if self.username is None:
                if not (username := input("Username: ").lower()) or len(username) > 16 or username == "server":
                    print("WARNING: Invalid username.")
                    continue
                self.username = username

                username_header = f"{len(self.username):<{HEADER_LENGTH}}".encode()
                self.client_socket.send(username_header + self.username.encode())
                continue

            message = input("")
            if message:
                message_header = f"{len(message):<{HEADER_LENGTH}}".encode()
                encoded_message = message.encode()
                self.client_socket.send(message_header + encoded_message)


class Client:
    def __init__(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((IP, PORT))
        self.client_socket.setblocking(False)

        self.keyboard_thread = KeyboardThread(self.client_socket)

        self.listen()

    def listen(self):
        while True:
            try:
                while True:
                    username_header = self.client_socket.recv(HEADER_LENGTH)
                    if not len(username_header):
                        print("WARNING: Connection closed by the server.")
                        sys.exit()

                    username_length = int(username_header.decode())
                    username = self.client_socket.recv(username_length).decode()

                    message_header = self.client_socket.recv(HEADER_LENGTH)
                    message_length = int(message_header.decode())
                    message = self.client_socket.recv(message_length).decode()

                    print(f"{username} > {message}")

            except IOError as e:
                if e.errno not in {errno.EAGAIN, errno.EWOULDBLOCK}:
                    print("Unexpected Reading Error:")
                    traceback.print_exception(e)
                    sys.exit()
                continue

            except Exception as e:
                print("Unexpected General Error:")
                traceback.print_exception(e)
                sys.exit(1)


if __name__ == "__main__":
    c = Client()
