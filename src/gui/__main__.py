import datetime
import threading
import sys

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLabel,
    QMainWindow,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLayout,
)

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


class Message(QWidget):
    def __init__(self, timestamp: int, author: str, content: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QVBoxLayout()

        timestamp_label = QLabel(datetime.datetime.fromtimestamp(timestamp).isoformat())
        author_label = QLabel(author)
        content_label = QLabel(content)

        header_layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        header_layout.addWidget(author_label, alignment=Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(timestamp_label, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(header_layout)
        layout.addWidget(content_label)

        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        self.setLayout(layout)

        self.setAutoFillBackground(True)

        p = self.palette()
        p.setColor(self.backgroundRole(), QColor.fromRgb(140, 179, 184))
        self.setPalette(p)


class MainWindow(QMainWindow):
    message_signal = Signal(int, str, str)

    def __init__(self):
        super().__init__()
        self.client_thread: ClientThread | None = None

        self.message_signal.connect(self.on_message)

        self.setWindowTitle("My Chat App")
        self.setFixedSize(1080, 720)

        self.username_input = QInputDialog()
        self.username_input.setLabelText("Username")
        self.username_input.accepted.connect(self.username_input_submitted)

        self.layout_ = QVBoxLayout()
        self.layout_.addWidget(self.username_input, alignment=Qt.AlignmentFlag.AlignCenter)

        widget = QWidget()
        widget.setLayout(self.layout_)

        widget.setAutoFillBackground(True)
        p = widget.palette()
        p.setColor(widget.backgroundRole(), QColor.fromRgb(103, 134, 135))
        widget.setPalette(p)

        self.setCentralWidget(widget)

    @Slot(str)
    def on_message(self, timestamp: int, author: str, msg: str):
        assert self.client_thread is not None, "must have client_thread attr set in order to receive messages"
        assert (
            self.client_thread.client is not None
        ), "must have client attr set on client_thread in order to receive messages"

        print(f"{self.client_thread.client.username.decode()} received the following message: {msg}")

        message = Message(timestamp, author, msg)
        self.layout_.addWidget(message, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    def username_input_submitted(self):
        if self.client_thread is not None:
            return

        if not (username := self.username_input.textValue()):
            return

        self.client_thread = ClientThread(username, self)
        print(f"created client for {username!r}")
        self.layout_.removeWidget(self.username_input)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
