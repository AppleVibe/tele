#!/usr/bin/env python3
import argparse
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import notes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rev", default="HEAD")
    args = parser.parse_args()
    options = SimpleNamespace(
        repo=str(Path(__file__).resolve().parent.parent),
        rev=args.rev,
        tag="v7.3.1-tele.1",
        previous="",
        upstream="v7.3.1",
        url="https://github.com/AppleVibe/tele",
    )
    body = notes.notes(options)
    assert len(body) <= 125000, len(body)
    assert "## download" in body
    assert "/docs/releases.md)" in body
    assert "<details>" not in body
    row = {"patches/tdesktop/example.patch": (1, "Example", "Settings")}
    with patch.object(notes, "changes", return_value=(["Example"], {}, row, [], [], [])):
        small = notes.notes(options)
    assert "<details>" in small
    assert "| [1]" in small
    print(f"Release notes limit passed: {len(body)} characters; small patch tables preserved.")


if __name__ == "__main__":
    main()
