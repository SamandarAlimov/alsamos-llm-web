"""safety.py — Sandbox xavfsizligi: blocklist va scope tekshiruvi.

- `rm -rf /` va shunga o'xshash halokatli buyruqlar BLOKLANADI.
- Tashqi IP scan (nmap, masscan, tashqi manzillarga ping-sweep) RAD ETILADI.
- Faqat ruxsat etilgan ish katalogi (scope) ichida ishlash.
"""
from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass

# Halokatli buyruq patternlari.
_BLOCKED_PATTERNS = [
    r"rm\s+-rf?\s+(/|~|\*|/\*|\$HOME)(\s|$)",
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",          # fork bomb
    r"\bmkfs\.",
    r"\bdd\b.*of=/dev/(sd|nvme|hd)",
    r">\s*/dev/(sd|nvme|hd)",
    r"\bchmod\s+-R\s+0*777\s+/",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r"\b(nmap|masscan|zmap)\b",                    # tarmoq skanerlash
    r"\bnc\b.*-l",                                  # netcat listener
    r"curl\s+.*\|\s*(sudo\s+)?(bash|sh)\b",         # remote pipe to shell
    r"wget\s+.*\|\s*(sudo\s+)?(bash|sh)\b",
    r"\b(iptables|ufw)\b",
]
_BLOCKED = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]


@dataclass
class SafetyVerdict:
    allowed: bool
    reason: str = ""

    def to_dict(self):
        return {"allowed": self.allowed, "reason": self.reason}


def check_command(command: str) -> SafetyVerdict:
    """Terminal buyrug'ini blocklist bo'yicha tekshiradi."""
    if not command or not command.strip():
        return SafetyVerdict(False, "Bo'sh buyruq.")
    for pat in _BLOCKED:
        if pat.search(command):
            return SafetyVerdict(False, f"Bloklangan pattern: {pat.pattern}")
    return SafetyVerdict(True, "OK")


def _is_private(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            resolved = socket.gethostbyname(host)
            ip = ipaddress.ip_address(resolved)
        except (socket.gaierror, ValueError):
            return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def check_network_target(host: str, allow_external: bool = False) -> SafetyVerdict:
    """Tashqi manzilga so'rov / skan urinishini tekshiradi."""
    if allow_external:
        return SafetyVerdict(True, "Tashqi ruxsat berilgan.")
    if _is_private(host):
        return SafetyVerdict(True, "Ichki/loopback manzil.")
    return SafetyVerdict(False, f"Tashqi manzilga ruxsatsiz kirish rad etildi: {host}")


def check_path_scope(path: str, allowed_root: str) -> SafetyVerdict:
    """Fayl yo'li ruxsat etilgan ildiz (scope) ichida ekanini tekshiradi."""
    import os
    real = os.path.realpath(path)
    root = os.path.realpath(allowed_root)
    if real == root or real.startswith(root + os.sep):
        return SafetyVerdict(True, "Scope ichida.")
    return SafetyVerdict(False, f"Scope tashqarisidagi yo'l rad etildi: {path}")
