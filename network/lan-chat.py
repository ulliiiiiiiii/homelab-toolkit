#!/usr/bin/env python3
"""Two-way text chat between two machines, peer to peer, without a server.

Usage: lan-chat.py PEER [--bind ADDRESS] [--port PORT]

Each message travels over its own TCP connection. Nothing is encrypted or
authenticated, so use it on a direct cable or a LAN you trust.
"""

from __future__ import annotations

import argparse
import socket
import threading
from collections.abc import Callable

DEFAULT_PORT = 5555


def local_address_for(peer: str) -> str:
    """The local address the kernel would use to reach `peer`.

    Listening on that address alone keeps the chat off every other interface. Connecting
    a UDP socket only looks up the route, it does not send anything.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((peer, 9))
        address: str = probe.getsockname()[0]
        return address


def listen(address: str, port: int) -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((address, port))
    server.listen()
    return server


def serve(server: socket.socket, on_message: Callable[[str, str], None]) -> None:
    """Pass every complete message to `on_message`. A message ends when the sender closes."""
    while True:
        connection, (sender, _) = server.accept()
        with connection:
            chunks = []
            while chunk := connection.recv(65536):
                chunks.append(chunk)
        if chunks:
            on_message(sender, b"".join(chunks).decode("utf-8", errors="replace"))


def send(peer: str, port: int, text: str, timeout: float = 3.0) -> None:
    with socket.create_connection((peer, port), timeout=timeout) as connection:
        connection.sendall(text.encode("utf-8"))


def show(sender: str, text: str) -> None:
    print(f"\r{sender}: {text}\n> ", end="", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Two-way text chat with another machine.")
    parser.add_argument("peer", help="address of the other machine")
    parser.add_argument("--bind", help="local address to listen on (default: towards PEER)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    address = args.bind or local_address_for(args.peer)
    server = listen(address, args.port)
    threading.Thread(target=serve, args=(server, show), daemon=True).start()
    print(f"chat {address} <-> {args.peer}:{args.port}, Ctrl+C to quit")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if text:
            try:
                send(args.peer, args.port, text)
            except OSError as error:
                print(f"not sent: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
