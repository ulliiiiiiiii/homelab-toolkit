import os

import pytest

SCRIPT = "ssh/ssh-harden.sh"


def test_help(sandbox):
    result = sandbox.run(SCRIPT, "--help")
    assert result.returncode == 0
    assert result.stdout.startswith("Switch sshd to key-only logins")


def test_needs_at_least_one_user(sandbox):
    result = sandbox.run(SCRIPT)
    assert result.returncode == 1
    assert "name at least one user" in result.stderr


def test_rejects_unknown_options(sandbox):
    result = sandbox.run(SCRIPT, "--yes", "alice")
    assert result.returncode == 1
    assert "unknown option --yes" in result.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="checks the refusal as a normal user")
def test_refuses_to_run_without_root(sandbox):
    result = sandbox.run(SCRIPT, "alice")
    assert result.returncode == 1
    assert "run as root" in result.stderr
