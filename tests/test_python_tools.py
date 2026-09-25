import queue
import threading

import pytest
from conftest import load

bounce = load("desktop/bounce-screensaver.py")
chat = load("network/lan-chat.py")


@pytest.mark.parametrize(
    ("position", "velocity", "expected"),
    [
        (10.0, 2.0, (12.0, 2.0)),
        (149.0, 2.0, (150.0, -2.0)),
        (1.0, -2.0, (0.0, 2.0)),
    ],
    ids=["moves", "bounces right", "bounces left"],
)
def test_step(position, velocity, expected):
    assert bounce.step(position, velocity, size=50, limit=200) == expected


def test_step_on_a_screen_smaller_than_the_image():
    assert bounce.step(0.0, 2.0, size=50, limit=30) == (0.0, -2.0)


def test_chat_delivers_long_messages_completely():
    server = chat.listen("127.0.0.1", 0)
    received = queue.Queue()
    threading.Thread(
        target=chat.serve, args=(server, lambda *message: received.put(message)), daemon=True
    ).start()
    text = "hello " * 20_000
    chat.send("127.0.0.1", server.getsockname()[1], text)
    assert received.get(timeout=5) == ("127.0.0.1", text)
    server.close()


def test_chat_listens_on_the_interface_towards_the_peer():
    assert chat.local_address_for("127.0.0.1") == "127.0.0.1"
