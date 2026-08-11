#!/usr/bin/env python3
"""Validate local references and external dependencies in the static site."""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {".git", "reports"}
TEXT_EXTS = {".html", ".css", ".js", ".svg"}
LOCAL_ATTRS = ("href", "src", "poster", "data-src", "data-image")
EXTERNAL_RE = re.compile(r"""(?:(?:https?:)?//)[^'"<>\s)]+""")
CSS_URL_RE = re.compile(r"url\((['\"]?)([^)'\"\s]+)\1\)")
ATTR_RE = re.compile(r"""\b(href|src|poster|data-src|data-image|srcset)=["']([^"']*)["']""", re.I)


def site_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix.lower() in TEXT_EXTS:
            files.append(path)
    return sorted(files)


def is_external(value: str) -> bool:
    return value.startswith(("http://", "https://", "//", "mailto:", "tel:", "data:", "javascript:", "#", "%23"))


def check_local(value: str, source: Path, missing: list[dict[str, str]]) -> None:
    value = value.strip()
    if not value or is_external(value):
        return
    if value in {"v5"}:
        return
    parsed = urlparse(value)
    if parsed.scheme:
        return
    path = unquote(parsed.path)
    if not path:
        return
    target = (source.parent / path).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        missing.append({"file": str(source.relative_to(ROOT)), "reference": value, "reason": "outside project"})
        return
    if not target.exists():
        missing.append({"file": str(source.relative_to(ROOT)), "reference": value, "reason": "missing"})


def main() -> int:
    missing: list[dict[str, str]] = []
    forbidden: list[dict[str, str]] = []
    external_domains: Counter[str] = Counter()

    for path in site_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in ATTR_RE.finditer(text):
            attr, value = match.groups()
            if attr.lower() == "srcset":
                for candidate in value.split(","):
                    url = candidate.strip().split(" ")[0] if candidate.strip() else ""
                    check_local(url, path, missing)
            else:
                check_local(value, path, missing)
        for match in CSS_URL_RE.finditer(text):
            check_local(match.group(2), path, missing)
        for url in EXTERNAL_RE.findall(text):
            parsed = urlparse(("https:" + url) if url.startswith("//") else url)
            if parsed.netloc and parsed.netloc not in {"www.w3.org", "schema.org"}:
                external_domains[parsed.netloc] += 1
        for pattern in ("file://", "chrome-extension://", "/Users/", "C:\\", "localhost"):
            if pattern.lower() in text.lower():
                forbidden.append({"file": str(path.relative_to(ROOT)), "pattern": pattern})

    squarespace_domains = {
        domain: count
        for domain, count in external_domains.items()
        if "squarespace" in domain
    }

    report = {
        "missing_local_references": missing,
        "forbidden_local_or_browser_paths": forbidden,
        "external_domains": dict(sorted(external_domains.items())),
        "squarespace_domains": squarespace_domains,
        "ok": not missing and not forbidden and not squarespace_domains,
    }
    out = ROOT / "reports" / "validation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
