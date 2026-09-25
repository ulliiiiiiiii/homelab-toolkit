import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def load(relative_path):
    """Import a script whose file name is not a valid module name."""
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Sandbox:
    """A temporary PATH with fake commands, and a way to run the scripts against it."""

    def __init__(self, tmp_path):
        self.root = tmp_path
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        self.log = tmp_path / "log"
        self.log.mkdir()
        self.env = {**os.environ, "PATH": f"{self.bin}:{os.environ['PATH']}", "LOG": str(self.log)}

    def fake(self, name, body):
        command = self.bin / name
        command.write_text(f"#!/bin/sh\n{body}\n")
        command.chmod(0o755)

    def run(self, script, *args, stdin="", **env):
        return subprocess.run(
            ["bash", str(ROOT / script), *args],
            input=stdin,
            capture_output=True,
            text=True,
            env={**self.env, **env},
            check=False,
        )


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(tmp_path)
