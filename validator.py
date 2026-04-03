#!/usr/bin/env python3
"""
Validator for Notepad++ macOS plugin list.

Validates pl.macos-arm64.json:
  - JSON schema conformance
  - Unique folder-name, display-name, and repository entries
  - Downloads each ZIP and verifies SHA-256 hash
  - Checks that ZIP contains {folder-name}.dylib

Optionally generates doc/plugin_list_macos_arm64.md (pass "md" argument).

Usage:
  python3 validator.py           # validate only
  python3 validator.py md        # validate + generate markdown
"""

import io
import json
import os
import sys
import zipfile
from hashlib import sha256
from urllib.request import urlopen, Request

has_error = False

PLUGIN_LIST = "pl.macos-arm64.json"
SCHEMA_FILE = "pl.schema"
DOC_OUTPUT = "doc/plugin_list_macos_arm64.md"


def post_error(message):
    global has_error
    has_error = True
    print(f"  ERROR: {message}", file=sys.stderr)


def validate_schema(pl):
    """Basic schema checks without requiring jsonschema package."""
    if "version" not in pl:
        post_error("Missing 'version' field")
    if "npp-plugins" not in pl:
        post_error("Missing 'npp-plugins' field")
        return

    required = ["folder-name", "display-name", "version", "id",
                 "repository", "description", "author", "homepage"]
    for i, plugin in enumerate(pl["npp-plugins"]):
        name = plugin.get("display-name", f"plugin[{i}]")
        for key in required:
            if key not in plugin:
                post_error(f"{name}: missing required field '{key}'")
        if "id" in plugin and len(plugin["id"]) != 64:
            post_error(f"{name}: 'id' must be a 64-character hex SHA-256 hash")


def validate_uniqueness(plugins):
    """Check that folder-name, display-name, and repository are unique."""
    seen_folders = {}
    seen_names = {}
    seen_repos = {}
    for plugin in plugins:
        name = plugin.get("display-name", "")
        folder = plugin.get("folder-name", "")
        repo = plugin.get("repository", "")

        if folder in seen_folders:
            post_error(f"{name}: duplicate folder-name '{folder}'")
        seen_folders[folder] = True

        if name in seen_names:
            post_error(f"{name}: duplicate display-name")
        seen_names[name] = True

        if repo in seen_repos:
            post_error(f"{name}: duplicate repository URL")
        seen_repos[repo] = True


def validate_plugin(plugin):
    """Download ZIP, verify hash, check for .dylib inside."""
    name = plugin["display-name"]
    url = plugin["repository"]
    expected_hash = plugin["id"].lower()
    dylib_name = f'{plugin["folder-name"]}.dylib'

    print(f"  Checking {name}...", end="", flush=True)

    # Try unauthenticated first, fall back to gh CLI for private repos
    data = None
    try:
        req = Request(url, headers={"User-Agent": "npp-macos-validator/1.0"})
        response = urlopen(req, timeout=60)
        data = response.read()
    except Exception:
        pass

    if data is None and "github.com/" in url:
        # For private repos, use gh CLI to download the release asset
        import subprocess, tempfile, re
        m = re.search(r"github\.com/([^/]+/[^/]+)/releases/download/([^/]+)/(.+)$", url)
        if m:
            repo, tag, asset_name = m.group(1), m.group(2), m.group(3)
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    result = subprocess.run(
                        ["gh", "release", "download", tag,
                         "--repo", repo,
                         "--pattern", asset_name,
                         "--dir", tmpdir],
                        capture_output=True, text=True, timeout=120)
                    if result.returncode == 0:
                        asset_path = os.path.join(tmpdir, asset_name)
                        if os.path.exists(asset_path):
                            with open(asset_path, "rb") as f:
                                data = f.read()
                except Exception:
                    pass

    if data is None:
        post_error(f"{name}: failed to download from {url}")
        return

    # Verify SHA-256
    actual_hash = sha256(data).hexdigest().lower()
    if actual_hash != expected_hash:
        print(" HASH MISMATCH")
        post_error(f"{name}: hash mismatch. Expected {expected_hash}, got {actual_hash}")
        return

    # Verify it's a valid ZIP
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        print(" BAD ZIP")
        post_error(f"{name}: invalid ZIP file")
        return

    # Check for .dylib (case-insensitive)
    found = False
    for entry in zf.namelist():
        if entry.lower().endswith(dylib_name.lower()):
            found = True
            break

    if not found:
        print(f" MISSING {dylib_name}")
        post_error(f"{name}: ZIP does not contain {dylib_name}")
        return

    print(" OK")


def gen_markdown(pl):
    """Generate a markdown table from the plugin list."""
    lines = []
    lines.append("## Plugin List — macOS ARM64\n")
    lines.append(f"Version {pl['version']}\n")
    lines.append("| Plugin name | Author | Homepage | Version and link | Description |")
    lines.append("|---|---|---|---|---|")

    for plugin in pl["npp-plugins"]:
        name = plugin["display-name"]
        author = plugin["author"]
        homepage = plugin["homepage"]
        version = plugin["version"]
        repo = plugin["repository"]
        descr = plugin["description"].replace("\n", "<br>").replace("|", "&vert;")

        # Truncate long descriptions with <details>
        if len(descr) > 100:
            i = descr.rfind(" ", 0, 100)
            if i == -1:
                i = 100
            summary = descr[:i]
            rest = descr[i:]
            descr_cell = f" <details> <summary> {summary} </summary> {rest} </details>"
        else:
            descr_cell = descr

        link = f"[{version} - macOS arm64]({repo})"
        lines.append(f"| {name} | {author} | {homepage} | {link} | {descr_cell} |")

    return "\n".join(lines) + "\n"


def main():
    generate_md = len(sys.argv) > 1 and sys.argv[1] == "md"

    # Load and validate
    print(f"Validating {PLUGIN_LIST}...")

    try:
        with open(PLUGIN_LIST) as f:
            pl = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        post_error(f"Cannot read {PLUGIN_LIST}: {e}")
        sys.exit(1)

    validate_schema(pl)
    plugins = pl.get("npp-plugins", [])
    validate_uniqueness(plugins)

    print(f"Found {len(plugins)} plugin(s). Downloading and verifying...")
    for plugin in plugins:
        validate_plugin(plugin)

    # Generate markdown
    if generate_md or not has_error:
        os.makedirs("doc", exist_ok=True)
        md = gen_markdown(pl)
        with open(DOC_OUTPUT, "w") as f:
            f.write(md)
        print(f"Generated {DOC_OUTPUT}")

    if has_error:
        print("\nValidation FAILED.", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nValidation passed.")


if __name__ == "__main__":
    main()
