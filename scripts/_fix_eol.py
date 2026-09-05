#!/usr/bin/env python3
"""Fix CRLF to LF in ci.yml."""
import pathlib

for name in ["ci.yml", "pre-commit.yml"]:
    p = pathlib.Path(f".github/workflows/{name}")
    content = p.read_text(encoding="utf-8")
    content = content.replace("\r\n", "\n")
    p.write_bytes(content.encode("utf-8"))
    raw = p.read_bytes()
    has_bom = raw[:3] == b'\xef\xbb\xbf'
    has_crlf = b'\r\n' in raw
    print(f"{name}: {len(raw)} bytes, BOM={has_bom}, CRLF={has_crlf}")
