#!/usr/bin/env python3
"""Scan stdin for potential secrets.

Reads text from standard input and searches for keywords commonly used in
credentials like "token", "secret", "password", or "api_key". If any matches
are found, messages are printed to stderr and the script exits with status 1.
"""
import re
import sys

PATTERN = re.compile(r"(token|secret|password|api[\s_-]*key)", re.IGNORECASE)


def main() -> int:
    data = sys.stdin.read()
    hits = []
    for i, line in enumerate(data.splitlines(), 1):
        if not line.startswith("+") or line.startswith("+++"):
            continue
        content = line[1:]
        if "Potential secret" in content:
            continue
        if PATTERN.search(content):
            hits.append(f"Potential secret at line {i}: {content.strip()}")
    if hits:
        print("\n".join(hits), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
