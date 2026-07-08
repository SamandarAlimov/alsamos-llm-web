"""code_exec.py — Sandbox ichida xavfsiz kod/buyruq ijrosi.

Har bir buyruq avval safety.check_command orqali tekshiriladi.
Faqat allowed_root (scope) ichida ishlaydi. Timeout bilan cheklangan.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass

from . import safety


@dataclass
class ExecResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    blocked_reason: str = ""

    def to_dict(self):
        return {"ok": self.ok, "stdout": self.stdout, "stderr": self.stderr,
                "returncode": self.returncode, "blocked_reason": self.blocked_reason}


def run_shell(command: str, cwd: str | None = None, timeout: int = 20) -> ExecResult:
    verdict = safety.check_command(command)
    if not verdict.allowed:
        return ExecResult(False, "", "", -1, blocked_reason=verdict.reason)
    workdir = cwd or tempfile.gettempdir()
    try:
        proc = subprocess.run(
            command, shell=True, cwd=workdir, capture_output=True,
            text=True, timeout=timeout,
        )
        return ExecResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired:
        return ExecResult(False, "", f"Timeout ({timeout}s) tugadi.", -1)


def run_python(code: str, timeout: int = 20) -> ExecResult:
    """Python kod parchasini alohida jarayonda ishga tushiradi."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        proc = subprocess.run(
            ["python3", path], capture_output=True, text=True, timeout=timeout,
        )
        return ExecResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired:
        return ExecResult(False, "", f"Timeout ({timeout}s) tugadi.", -1)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
