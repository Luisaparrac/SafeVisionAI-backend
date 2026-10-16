"""Documentation and examples carry no infrastructure data, only markers.

Checks every Markdown file and environment example tracked by git: no hosting
or cloud host names, no e-mail outside example.com and no IP outside the
ranges reserved for documentation (RFC 5737), loopback and 0.0.0.0.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = ["*.md", ".env.example", ".env.compose.example", "*.sql"]

FORBIDDEN_WORDS = re.compile(r"azure|onrender|vercel", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ALLOWED_IP_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.", "127.0.0.1", "0.0.0.0")


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", *PATTERNS], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [ROOT / name for name in result.stdout.splitlines()]


FILES = tracked_files()


def test_there_is_documentation_to_check():
    assert any(path.name == "README.md" for path in FILES)


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_infrastructure_data(path):
    text = path.read_text(encoding="utf-8")
    assert not FORBIDDEN_WORDS.findall(text)
    domains = {match.group(1).lower() for match in EMAIL.finditer(text)}
    assert domains <= {"example.com", "example.org"}
    assert all(ip.startswith(ALLOWED_IP_PREFIXES) for ip in IP.findall(text))
