#!/usr/bin/env python3
"""Check the Product Roadmap Captain repository before a release.

Uses the Python standard library only. Run from the repository root:

    python3 scripts/check.py

Exits with status 1 and lists every problem found, or prints "All checks passed."
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "product-roadmap-captain"
SKILL_FILE = SKILL_DIR / "SKILL.md"
PLUGIN_FILE = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_FILE = ROOT / ".claude-plugin" / "marketplace.json"

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
LINK_PATTERN = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")

# Lines every roadmap must end with. They are checked in SKILL.md and outputs.md.
CLOSING_LINES = (
    "Every figure comes from the founder. Calculations show their working.",
    "Built with Product Roadmap Captain, created by Nastasha Velasco. Nothing here is legal advice.",
)

# Patterns that must never appear in a published file.
FORBIDDEN = {
    "API key": re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "password assignment": re.compile(r"(?i)\b(password|passwd|secret)\s*[:=]\s*\S+"),
    "email address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
}

# Placeholders that must be filled in before publishing.
PLACEHOLDERS = ("GITHUB_USERNAME",)

# Words replaced during review. They must not come back.
RETIRED_TERMS = ("unproven", "load-bearing", "kill list", "wedge", "held-back")

TEXT_SUFFIXES = {".md", ".json", ".txt", ".py", ".yml", ".yaml"}


def parse_frontmatter(text: str) -> dict[str, str]:
    """Return the simple key: value pairs between the first two --- lines."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def check_skill(problems: list[str]) -> None:
    if not SKILL_FILE.is_file():
        problems.append("skills/product-roadmap-captain/SKILL.md is missing")
        return
    text = SKILL_FILE.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)

    name = meta.get("name", "")
    if not name:
        problems.append("SKILL.md: frontmatter has no name")
    elif not NAME_PATTERN.match(name) or len(name) > 64:
        problems.append(f"SKILL.md: name '{name}' must be lowercase words joined by hyphens, at most 64 characters")
    elif name != SKILL_DIR.name:
        problems.append(f"SKILL.md: name '{name}' does not match its folder '{SKILL_DIR.name}'")

    description = meta.get("description", "")
    if not description:
        problems.append("SKILL.md: frontmatter has no description")
    elif len(description) > 1024:
        problems.append(f"SKILL.md: description is {len(description)} characters; the limit is 1024")

    if not meta.get("license"):
        problems.append("SKILL.md: frontmatter has no license")

    for line in CLOSING_LINES:
        if line not in text:
            problems.append(f"SKILL.md: closing line missing: {line}")

    # Every reference file is linked from SKILL.md, and longer ones have a table of contents.
    for ref in sorted((SKILL_DIR / "references").glob("*.md")):
        relative = f"references/{ref.name}"
        if f"]({relative})" not in text:
            problems.append(f"SKILL.md: does not link to {relative}")
        ref_text = ref.read_text(encoding="utf-8")
        if len(ref_text.splitlines()) > 100 and "## Contents" not in ref_text:
            problems.append(f"{relative}: over 100 lines with no '## Contents' section")

    outputs = (SKILL_DIR / "references" / "outputs.md").read_text(encoding="utf-8")
    for line in CLOSING_LINES:
        if line not in outputs:
            problems.append(f"references/outputs.md: closing line missing: {line}")


def check_manifests(problems: list[str]) -> None:
    try:
        plugin = json.loads(PLUGIN_FILE.read_text(encoding="utf-8"))
        marketplace = json.loads(MARKETPLACE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        problems.append(f".claude-plugin: cannot read the manifests ({error})")
        return

    if plugin.get("name") != SKILL_DIR.name:
        problems.append("plugin.json: name must match the skill folder")
    if not SEMVER_PATTERN.match(str(plugin.get("version", ""))):
        problems.append("plugin.json: version must look like 1.0.0")
    if plugin.get("license") != "MIT":
        problems.append("plugin.json: license must be MIT")

    listed = [entry.get("name") for entry in marketplace.get("plugins", [])]
    if plugin.get("name") not in listed:
        problems.append("marketplace.json: does not list the plugin by its name")
    if marketplace.get("name") != plugin.get("name"):
        problems.append("marketplace.json: name must match the plugin name used in the install command")


def check_files(problems: list[str]) -> None:
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.suffix not in TEXT_SUFFIXES:
            continue
        if path == Path(__file__).resolve():
            continue
        relative = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")

        for label, pattern in FORBIDDEN.items():
            if pattern.search(text):
                problems.append(f"{relative}: contains what looks like an {label}")

        for placeholder in PLACEHOLDERS:
            if placeholder in text:
                problems.append(f"{relative}: still contains the placeholder {placeholder}")

        lowered = text.lower()
        for term in RETIRED_TERMS:
            if term in lowered:
                problems.append(f"{relative}: uses the retired term '{term}'")

        if path.suffix == ".md":
            for target in LINK_PATTERN.findall(text):
                if "://" in target or target.startswith("mailto:"):
                    continue
                if not (path.parent / target).exists():
                    problems.append(f"{relative}: link to '{target}' does not resolve")


def main() -> int:
    problems: list[str] = []
    check_skill(problems)
    check_manifests(problems)
    check_files(problems)
    if problems:
        print(f"{len(problems)} problem(s) found:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
