SCRIPT = "desktop/idle-watch.sh"


def test_help(sandbox):
    result = sandbox.run(SCRIPT, "-h")
    assert result.returncode == 0
    assert result.stdout.startswith("Run a command whenever a GNOME session")


def test_needs_a_command(sandbox):
    result = sandbox.run(SCRIPT, "-t", "60")
    assert result.returncode == 2
    assert "usage" in result.stderr
