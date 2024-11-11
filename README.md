# Python Chat App

## Usage
Start a server:
```shell
python3.13 -m src.server
```
Start a client:
```shell
python3.13 -m src.client
```

Once a client is connected to a server, it can send messages by entering the message and pressing enter.
The connected client will also receive messages sent from other clients and the server.

Currently the server will send welcome messages, "{user} has joined the chat" messages, and "{user} has left the chat" messages.

All messages sent from the server include:
- a timestamp for when the server dispatched the message
- the author of the message being sent
- the message content itself

Each of these three items has its own header.