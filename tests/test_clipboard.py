import stat

import pytest


@pytest.fixture
def clipboard(sandbox):
    runtime = sandbox.root / "run"
    runtime.mkdir(mode=0o700)
    sandbox.fake("ssh", 'n=$(ls "$LOG" | grep -c "^ssh") ; cat > "$LOG/ssh.$n"')
    sandbox.fake("wl-copy", 'cat > "$LOG/wl-copy"')

    class Clipboard:
        state = runtime / "clipboard-sync"

        def push(self, content):
            result = sandbox.run(
                "clipboard/clipboard-push.sh", "peer", stdin=content, XDG_RUNTIME_DIR=str(runtime)
            )
            assert result.returncode == 0, result.stderr

        def receive(self, content):
            result = sandbox.run(
                "clipboard/clipboard-recv.sh", stdin=content, XDG_RUNTIME_DIR=str(runtime)
            )
            assert result.returncode == 0, result.stderr

        def sent(self):
            return [path.read_text() for path in sorted(sandbox.log.glob("ssh.*"))]

        def copied(self):
            return (sandbox.log / "wl-copy").read_text()

    return Clipboard()


def test_new_content_goes_to_the_peer(clipboard):
    clipboard.push("first")
    clipboard.push("second")
    assert clipboard.sent() == ["first", "second"]


def test_unchanged_and_empty_content_is_not_sent(clipboard):
    clipboard.push("same")
    clipboard.push("same")
    clipboard.push("")
    assert clipboard.sent() == ["same"]


def test_received_content_is_not_sent_back(clipboard):
    clipboard.receive("from the peer")
    assert clipboard.copied() == "from the peer"
    clipboard.push("from the peer")
    assert clipboard.sent() == []


def test_state_is_private(clipboard):
    clipboard.push("password123")
    assert stat.S_IMODE(clipboard.state.stat().st_mode) == 0o700
    assert stat.S_IMODE((clipboard.state / "last").stat().st_mode) == 0o600


def test_push_needs_a_runtime_dir(sandbox):
    env = {"XDG_RUNTIME_DIR": ""}
    result = sandbox.run("clipboard/clipboard-push.sh", "peer", stdin="x", **env)
    assert result.returncode != 0
    assert "XDG_RUNTIME_DIR" in result.stderr
