import select
import socket
import time
from typing import Literal, TypedDict

from src.backend.constants import HEADER_LENGTH, SERVER_USERNAME

IP = "127.0.0.1"
PORT = 5001


class Message(TypedDict):
    data: bytes
    header: bytes


class Server:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((IP, PORT))
        self.server_socket.listen()

        print(f"INFO: Server started on {IP}:{PORT}.")

        self.sockets: list[socket.socket] = [self.server_socket]
        self.clients: dict[socket.socket, Message] = {}

        self.listen()

    @property
    def formatted_member_count(self):
        return "1 member" if (num_clients := len(self.clients)) == 1 else f"{num_clients} members"

    @property
    def known_usernames(self):
        return {joining_msg.get("data") for joining_msg in self.clients.values()}

    @staticmethod
    def decode_message(message: Message):
        return message["data"].decode()

    @staticmethod
    def format_peername(peername: tuple[str, int]) -> str:
        return f"{peername[0]}:{peername[1]}"

    @staticmethod
    def generate_message_header(message: str | bytes):
        if isinstance(message, str):
            # We must encode the message before getting the length, since the length may change when encoding
            # E.g. len("😀") == 1 but len("😀".encode()) == 4
            message = message.encode()

        return f"{len(message):<{HEADER_LENGTH}}".encode()

    @staticmethod
    def receive_message(client_socket: socket.socket) -> Message | Literal[False]:
        client_socket.settimeout(10)
        try:
            message_header = client_socket.recv(HEADER_LENGTH)
            if not message_header:
                return False

            message_length = int(message_header.decode())
            return {"data": client_socket.recv(message_length), "header": message_header}
        except socket.timeout:
            print(
                f"INFO: Timed out when attempting to establish connection with {Server.format_peername(client_socket.getpeername())}"
            )
            Server.send_message_to(
                client_socket, author=SERVER_USERNAME, message="ERR: timed out whilst waiting for username"
            )
            client_socket.close()
            return False
        except Exception as e:
            print(e)
            print(f"WARNING: Client {Server.format_peername(client_socket.getpeername())} closed connection.")
            return False

    @staticmethod
    def send_message_to(recipient: socket.socket, *, author: str | Message, message: str | Message):
        current_timestamp = str(int(time.time())).encode()
        current_timestamp_header = Server.generate_message_header(current_timestamp)

        if isinstance(author, str):
            encoded_author = author.encode()
            author_header = Server.generate_message_header(encoded_author)
        else:
            encoded_author = author["data"]
            author_header = author["header"]

        if isinstance(message, str):
            encoded_message = message.encode()
            message_header = Server.generate_message_header(encoded_message)
        else:
            encoded_message = message["data"]
            message_header = message["header"]

        recipient.send(
            current_timestamp_header
            + current_timestamp
            + author_header
            + encoded_author
            + message_header
            + encoded_message
        )

    def get_pending_messages(self) -> tuple[list[socket.socket], list[socket.socket]]:
        read_sockets, _, exception_sockets = select.select(self.sockets, [], self.sockets)
        return read_sockets, exception_sockets

    def handle_lost_connection(self, lost_socket: socket.socket):
        lost_username = self.decode_message(self.clients[lost_socket])
        print(
            f"INFO: Lost connection to {self.format_peername(lost_socket.getpeername())} (username: {lost_username})."
        )

        self.sockets.remove(lost_socket)
        del self.clients[lost_socket]

        message = f"{lost_username} has left the chat. There's now {self.formatted_member_count} online."
        for client_socket in self.clients:
            self.send_message_to(client_socket, author=SERVER_USERNAME, message=message)

    def handle_new_connection(self, joining_socket: socket.socket):
        joining_client_address = self.format_peername(joining_socket.getpeername())

        connecting_message = self.receive_message(joining_socket)
        if connecting_message is False:
            return

        joining_username = self.decode_message(connecting_message)
        if not self.validate_username(joining_username):
            self.send_message_to(
                joining_socket, author=SERVER_USERNAME, message="ERR: The provided username is invalid."
            )
            joining_socket.close()
            return

        print(f"INFO: Accepted new connection from {joining_client_address} (username: {joining_username}).")

        self.sockets.append(joining_socket)
        self.clients[joining_socket] = connecting_message

        # Send a welcome message to the new user
        self.send_message_to(
            joining_socket,
            author=SERVER_USERNAME,
            message=f"Welcome to the chat, {joining_username}! There's currently {self.formatted_member_count} online.",
        )

        # Announce the new user to all other users
        for client_socket in self.clients:
            if client_socket == joining_socket:
                continue

            self.send_message_to(
                client_socket,
                author=SERVER_USERNAME,
                message=f"{joining_username} has joined the chat. There's currently {self.formatted_member_count} online.",
            )

    def listen(self):
        while True:
            read_sockets, exception_sockets = self.get_pending_messages()

            for notified_socket in read_sockets:
                if notified_socket == self.server_socket:
                    client_socket = self.server_socket.accept()[0]
                    self.handle_new_connection(client_socket)
                else:
                    message = self.receive_message(notified_socket)

                    user_join_message = self.clients[notified_socket]

                    if message is False:
                        print(
                            f"INFO: Closed connection with {self.decode_message(user_join_message)} ({self.format_peername(notified_socket.getpeername())})."
                        )
                        self.handle_lost_connection(notified_socket)
                        continue

                    print(
                        f"CHAT: Received message from {self.format_peername(notified_socket.getpeername())}: {self.decode_message(message)}"
                    )

                    # Forward message to all other chat clients/members
                    for client_socket in self.clients:
                        if client_socket == notified_socket:
                            # Has already received this message, so don't send again
                            continue

                        self.send_message_to(client_socket, author=user_join_message, message=message)

            for exception_socket in exception_sockets:
                print(
                    f"WARNING: Exception occurred in {self.format_peername(exception_socket.getpeername())} (username: {self.decode_message(self.clients[exception_socket])})."
                )
                self.handle_lost_connection(exception_socket)

    def validate_username(self, username: str):
        if not username:
            # Username cannot be empty
            return False

        if username == SERVER_USERNAME:
            # Username cannot mimic the server
            return False

        if any(char.isupper() for char in username):
            # Usernames must be all lowercase
            # NB: Can't use `username.islower()` since that's `False` for usernames with non-letters
            # NB: This restriction may be a bug in Python -- `"3".islower() == False` but `"3a".islower() == True`.
            return False

        encoded_username = username.encode()
        if len(encoded_username) > 16:
            # Usernames must be at most 16 characters
            return False

        if encoded_username in self.known_usernames:
            # Usernames must be unique
            return False

        return True


if __name__ == "__main__":
    s = Server()
