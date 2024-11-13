import threading
import sys

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QInputDialog, QVBoxLayout, QWidget


from src.backend.client import Client


class ClientThread(threading.Thread):
    def __init__(self, username: str, app: "MainWindow"):
        self.username = username
        self.app = app
        self.client = None

        super().__init__(name=f"ClientThread{self.username}")

        self.start()

    def run(self):
        self.client = Client(self.username, self.app)
        self.client.listen()


class MainWindow(QMainWindow):
    message_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.client_thread: ClientThread | None = None

        self.message_signal.connect(self.on_message)

        self.setWindowTitle("My Chat App")
        self.setFixedSize(1080, 720)

        self.username_input = QInputDialog()
        self.username_input.setLabelText("Username")
        self.username_input.accepted.connect(self.username_input_submitted)

        layout = QVBoxLayout()
        layout.addWidget(self.username_input)

        widget = QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

    @Slot(str)
    def on_message(self, msg):
        assert self.client_thread is not None, "must have client_thread attr set in order to receive messages"
        assert (
            self.client_thread.client is not None
        ), "must have client attr set on client_thread in order to receive messages"

        print(f"{self.client_thread.client.username.decode()} received the following message: {msg}")

    def username_input_submitted(self):
        if self.client_thread is not None:
            return

        if not (username := self.username_input.textValue()):
            return

        print(repr(username))
        self.client_thread = ClientThread(username, self)
        print(f"created client for {username}")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
