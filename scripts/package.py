#!/usr/bin/env python3
"""Create a deterministic member archive from an explicit public-file allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(output: Path):
    if output.exists():
        raise ValueError("Output already exists; choose a new archive name")
    if not (ROOT / "host/build/main.js").is_file():
        raise ValueError("Build host/ before packaging")
    files = []
    for name in ["README.md", "INSTALL.md", "LICENSE", ".codex-plugin", ".claude-plugin", "skills", "docs", "scripts", "integrations", "host/build"]:
        source = ROOT / name
        if not source.exists():
            raise ValueError(f"Required package input missing: {name}")
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for item in candidates:
            if item.is_symlink():
                raise ValueError("Package input contains symlink")
            if not item.is_file() or "__pycache__" in item.parts or item.name.startswith("test_") or item.suffix == ".pyc":
                continue
            relative = item.relative_to(ROOT).as_posix()
            content = item.read_bytes()
            if item.suffix in {".md", ".json", ".py", ".js", ".cjs", ".toml"}:
                text = content.decode("utf-8")
                # Source code regex literals may contain the marker. Actual paths/keys must not.
                if re.search(r"/Users/[A-Za-z0-9._-]+/|sk-ant-[A-Za-z0-9_-]{15,}|ghp_[A-Za-z0-9]{20,}|xoxb-[0-9A-Za-z-]{20,}", text):
                    raise ValueError(f"Potential private path or credential in {relative}")
            files.append((relative, item, content))
    index = {relative: hashlib.sha256(content).hexdigest() for relative, _, content in files}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, item, content in files:
            info = zipfile.ZipInfo("agentic-os-codex-addon/" + relative, (2026, 9, 9, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | stat.S_IMODE(item.stat().st_mode)) << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED)
        archive.writestr("agentic-os-codex-addon/PACKAGE-SHA256.json", json.dumps(index, indent=2) + "\n")
    return {"archive": str(output.resolve()), "files": len(files), "bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.output), indent=2))
