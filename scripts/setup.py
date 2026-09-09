#!/usr/bin/env python3
"""Explicit, local, reviewable setup for the optional Agentic OS Codex companion."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "agentic-os-codex"
VERSION = "0.1.0"


class SetupError(Exception):
    pass


def digest(data: bytes | None) -> str | None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise SetupError(f"Invalid JSON at {path.name}; existing file was not changed") from exc


def regular_path(path: Path) -> Path:
    """Reject symlink redirection without silently normalizing an attacker supplied path."""
    path = Path(os.path.abspath(path.expanduser()))
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise SetupError(f"Symlink path requires manual review: {part}")
        if part.exists() and part != path and not part.is_dir():
            raise SetupError(f"Parent is not a directory: {part}")
    if path.exists() and not path.is_file():
        raise SetupError(f"Target is not a regular file: {path}")
    return path


def context(vault: Path, home: Path) -> tuple[Path, Path]:
    vault, home = vault.expanduser().resolve(), home.expanduser().resolve()
    if not vault.is_dir() or not home.is_dir():
        raise SetupError("Vault and home must exist as directories")
    if vault == home or vault == Path(vault.anchor):
        raise SetupError("Choose a specific vault folder, not your home or filesystem root")
    return vault, home


def allowed_target(path: Path, vault: Path, home: Path) -> Path:
    path = regular_path(path)
    allowed = [vault / ".obsidian/plugins" / PLUGIN_ID,
               vault / ".agents/skills", home / ".codex"]
    if not any(path.is_relative_to(root) and path != root for root in allowed):
        raise SetupError(f"Target outside the selected installation scope: {path}")
    # Authentication state is owned exclusively by the native applications.
    if path.name in {"auth.json", "credentials.json", ".credentials.json"}:
        raise SetupError("Installer cannot write authentication files")
    return path


def inventory(vault: Path, home: Path) -> dict:
    vault, home = context(vault, home)
    base = vault / ".obsidian/plugins/agentic-os"
    manifest = read_json(base / "manifest.json", {})
    sources = base / "src"
    enabled = read_json(vault / ".obsidian/community-plugins.json", [])
    if not isinstance(enabled, list):
        raise SetupError("Obsidian community-plugins.json is not a list")
    result = {
        "schema": 1, "version": VERSION, "vault": str(vault), "home": str(home),
        "platform": sys.platform, "architecture": platform.machine(),
        "supported_host_install": sys.platform == "darwin",
        "agentic_os": {"present": base.is_dir(), "version": manifest.get("version"),
                       "enabled": "agentic-os" in enabled,
                       "has_sources": sources.is_dir(),
                       "has_codex_provider": (sources / "providers/codex.ts").is_file(),
                       "main_sha256": digest((base / "main.js").read_bytes()) if (base / "main.js").is_file() else None},
        "companion": {"present": (base.parent / PLUGIN_ID / "manifest.json").is_file(),
                      "enabled": PLUGIN_ID in enabled},
        "binaries": {name: shutil.which(name) for name in ("claude", "codex", "node")},
        "agents": [], "skills": [],
    }
    for kind in ("agents", "skills"):
        names = set()
        for folder in [home / ".claude" / kind, vault / ".claude" / kind]:
            if folder.is_dir() and not folder.is_symlink():
                for item in folder.iterdir():
                    if item.is_symlink():
                        continue
                    if kind == "agents" and item.is_file() and item.suffix == ".md":
                        names.add(item.stem)
                    elif kind == "skills" and item.is_dir() and (item / "SKILL.md").is_file():
                        names.add(item.name)
        result[kind] = sorted(names)
    return result


def host_changes(vault: Path) -> list[dict]:
    build = ROOT / "host/build"
    if not (build / "manifest.json").is_file() or not (build / "main.js").is_file():
        raise SetupError("Host build missing. Build host/ first; no target files changed")
    meta = read_json(build / "manifest.json")
    if meta.get("id") != PLUGIN_ID:
        raise SetupError("Unexpected host plugin id")
    changes = []
    plugin = vault / ".obsidian/plugins" / PLUGIN_ID
    ownership_path = regular_path(plugin / ".addon-owned.json")
    ownership = read_json(ownership_path, {"files": {}})
    fingerprints = {}
    for source in sorted(build.rglob("*")):
        if source.is_symlink():
            raise SetupError("Host bundle contains a symlink")
        if not source.is_file():
            continue
        relative = source.relative_to(build)
        # User settings are never part of the distributable host payload.
        if relative.name in {"data.json", "auth.json", ".env"}:
            raise SetupError(f"Unexpected private file in host bundle: {relative}")
        target = regular_path(plugin / relative)
        before = target.read_bytes() if target.exists() else None
        after = source.read_bytes()
        old_hash = ownership.get("files", {}).get(relative.as_posix())
        if before != after and ((before is not None and old_hash != digest(before)) or (before is None and old_hash is not None)):
            raise SetupError(f"Companion file has untracked member changes; integration required: {relative}")
        fingerprints[relative.as_posix()] = digest(after)
        changes.append({"path": str(target), "before": before,
                        "after": after, "mode": stat.S_IMODE(source.stat().st_mode), "kind": "host"})
    managed = (json.dumps({"version": VERSION, "files": fingerprints}, sort_keys=True, indent=2) + "\n").encode()
    changes.append({"path": str(ownership_path), "before": ownership_path.read_bytes() if ownership_path.exists() else None,
                    "after": managed, "kind": "host-ownership"})
    return changes


def make_plan(vault: Path, home: Path, mode: str, agents: list[str], skills: list[str], mcps: list[str]) -> dict:
    vault, home = context(vault, home)
    info = inventory(vault, home)
    if mode == "claude-only":
        return {"inventory": info, "mode": mode, "changes": [], "statuses": [], "manual_steps": []}
    configured_home = os.environ.get("CODEX_HOME")
    if home == Path.home().resolve() and configured_home and Path(configured_home).expanduser().resolve() != home / ".codex":
        raise SetupError("Custom CODEX_HOME requires a dedicated migration; no standard-home changes planned")
    if sys.platform != "darwin":
        raise SetupError("Codex companion installation is currently macOS-only; inspect works on other platforms")
    if not info["agentic_os"]["present"]:
        raise SetupError("Install the base Agentic OS first, then rerun this optional setup")
    if not (vault / ".obsidian/plugins/agentic-os/main.js").is_file():
        raise SetupError("Base Agentic OS main.js is missing; repair the base installation first")
    sys.path.insert(0, str(ROOT))
    from integrations.planner import build_changes
    planned = build_changes(home, vault, agents, skills, mcps)
    changes = host_changes(vault) + planned["changes"]
    seen = set()
    filtered = []
    for change in changes:
        path = allowed_target(Path(change["path"]), vault, home)
        if str(path) in seen:
            raise SetupError(f"Two operations target the same file: {path}")
        seen.add(str(path))
        if change["before"] != change["after"]:
            filtered.append({**change, "path": str(path)})
    steps = list(planned["manual_steps"])
    if not info["binaries"]["codex"]:
        steps.insert(0, "Install the official Codex CLI following https://developers.openai.com/codex/cli/ and rerun doctor")
    steps.extend([
        "Run codex login in your own terminal if not yet authenticated",
        "Enable Agentic OS Codex in Obsidian community plugin settings when your sessions are ready",
        "Open the companion Codex pane and verify a harmless request with each selected role",
        "Verify each selected MCP with a harmless read inside the actual Codex session; configuration is not a tool test",
    ])
    return {"inventory": info, "mode": mode, "changes": filtered,
            "statuses": planned["statuses"], "manual_steps": steps}


def atomic_write(path: Path, data: bytes, mode: int = 0o600):
    regular_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    regular_path(path)
    fd, tmp = tempfile.mkstemp(prefix=".aos-stage-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def stage(plan: dict, output: Path) -> dict:
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise SetupError("Choose a new staging directory; existing plans are never overwritten")
    regular_path(output / "manifest.json")
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    payload = output / "payload"
    payload.mkdir(mode=0o700)
    files = []
    for i, change in enumerate(plan["changes"]):
        blob = f"payload/{i:04d}.bin"
        atomic_write(output / blob, change["after"])
        files.append({"path": change["path"], "before": digest(change["before"]),
                      "after": digest(change["after"]), "blob": blob,
                      "mode": change.get("mode", 0o600), "kind": change["kind"]})
    manifest = {"schema": 1, "version": VERSION, "mode": plan["mode"],
                "vault": plan["inventory"]["vault"], "home": plan["inventory"]["home"],
                "files": files, "statuses": plan["statuses"], "manual_steps": plan["manual_steps"],
                "created": datetime.now(timezone.utc).isoformat()}
    raw = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    atomic_write(output / "manifest.json", raw)
    return {"plan": str(output), "sha256": digest(raw), "files": len(files),
            "statuses": plan["statuses"], "manual_steps": plan["manual_steps"]}


def load_plan(folder: Path, expected_sha: str) -> tuple[dict, list[tuple[dict, Path, bytes]]]:
    folder = folder.expanduser().absolute()
    raw = regular_path(folder / "manifest.json").read_bytes()
    if digest(raw) != expected_sha:
        raise SetupError("Plan hash differs from the reviewed manifest")
    manifest = json.loads(raw)
    if manifest.get("schema") != 1 or manifest.get("mode") not in {"codex", "claude-only"}:
        raise SetupError("Unsupported plan")
    vault, home = context(Path(manifest["vault"]), Path(manifest["home"]))
    operations = []
    seen = set()
    for entry in manifest["files"]:
        target = allowed_target(Path(entry["path"]), vault, home)
        if str(target) in seen:
            raise SetupError("Duplicate target in plan")
        seen.add(str(target))
        blob = folder / entry["blob"]
        if not blob.absolute().is_relative_to(folder / "payload") or ".." in Path(entry["blob"]).parts:
            raise SetupError("Payload outside staging directory")
        content = regular_path(blob).read_bytes()
        if digest(content) != entry["after"]:
            raise SetupError("Payload hash mismatch")
        mode = entry.get("mode", 0o600)
        if not isinstance(mode, int) or mode < 0 or mode > 0o777:
            raise SetupError("Unsafe permission mode")
        operations.append((entry, target, content))
    if manifest["mode"] == "claude-only" and operations:
        raise SetupError("Claude-only plans cannot mutate files")
    return manifest, operations


def write_state(folder: Path, state: dict):
    atomic_write(folder / "transaction.json", (json.dumps(state, indent=2) + "\n").encode())


def apply(folder: Path, expected_sha: str) -> dict:
    folder = folder.expanduser().absolute()
    manifest, operations = load_plan(folder, expected_sha)
    if manifest["mode"] == "codex" and sys.platform != "darwin":
        raise SetupError("Codex host installation is currently macOS-only")
    lock = folder / "transaction.lock"
    regular_path(lock)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SetupError("Another transaction is running; do not retry until it finishes") from exc
    os.close(fd)
    try:
        previous = read_json(folder / "transaction.json", {})
        if previous.get("state") == "applied":
            for entry, target, _ in operations:
                if not target.exists() or digest(target.read_bytes()) != entry["after"]:
                    raise SetupError("Installed files changed after apply; create a new plan")
            return {"state": "already-applied", "files": len(operations)}
        if previous:
            raise SetupError("Existing transaction needs rollback or a new plan")
        # Preflight every target before making the first target write.
        for entry, target, _ in operations:
            current = target.read_bytes() if target.exists() else None
            if digest(current) != entry["before"]:
                raise SetupError(f"File changed since inspection: {target}")
        state = {"state": "applying", "manifest_sha256": expected_sha, "files": []}
        write_state(folder, state)
        backups = folder / "backups"
        backups.mkdir(mode=0o700)
        for i, (entry, target, content) in enumerate(operations):
            regular_path(target)
            current = target.read_bytes() if target.exists() else None
            if digest(current) != entry["before"]:
                raise SetupError(f"Concurrent change detected: {target}")
            backup = f"backups/{i:04d}.bin" if current is not None else None
            old_mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
            if backup:
                atomic_write(folder / backup, current)
            state["files"].append({"path": str(target), "before": entry["before"], "after": entry["after"],
                                   "backup": backup, "old_mode": old_mode})
            # Journal before mutation so a terminated process can be rolled back.
            write_state(folder, state)
            atomic_write(target, content, old_mode if old_mode is not None else entry["mode"])
        state["state"] = "applied"
        write_state(folder, state)
        return {"state": "applied", "files": len(operations), "manual_steps": manifest["manual_steps"]}
    except Exception:
        # Keep the journal and backups for explicit conflict-aware rollback.
        raise
    finally:
        lock.unlink(missing_ok=True)


def _rollback_unlocked(folder: Path, expected_sha: str) -> dict:
    folder = folder.expanduser().absolute()
    manifest, operations = load_plan(folder, expected_sha)
    state = read_json(regular_path(folder / "transaction.json"), {})
    if state.get("manifest_sha256") != expected_sha:
        raise SetupError("No matching transaction journal")
    if state.get("state") == "rolled-back":
        return {"state": "already-rolled-back"}
    by_path = {str(target): entry for entry, target, _ in operations}
    restore = []
    for item in state["files"]:
        target = allowed_target(Path(item["path"]), Path(manifest["vault"]), Path(manifest["home"]))
        entry = by_path.get(str(target))
        if entry is None or item["before"] != entry["before"] or item["after"] != entry["after"]:
            raise SetupError("Journal differs from reviewed plan")
        current = digest(target.read_bytes() if target.exists() else None)
        if current == item["before"]:
            continue
        if current != item["after"]:
            raise SetupError(f"User changed this file after installation; rollback stopped: {target}")
        backup_data = None
        if item["backup"] is not None:
            relative = Path(item["backup"])
            if relative.is_absolute() or ".." in relative.parts or relative.parts[0] != "backups":
                raise SetupError("Invalid backup path")
            backup_data = regular_path(folder / relative).read_bytes()
            if digest(backup_data) != item["before"]:
                raise SetupError("Backup hash mismatch")
        restore.append((item, target, backup_data))
    archive = folder / "rollback-archive"
    archive.mkdir(mode=0o700, exist_ok=True)
    for i, (item, target, content) in enumerate(reversed(restore)):
        regular_path(target)
        if digest(target.read_bytes()) != item["after"]:
            raise SetupError("Concurrent change during rollback; remaining files preserved")
        if content is None:
            destination = regular_path(archive / f"{i:04d}-{target.name}")
            if destination.exists():
                raise SetupError("Rollback archive already exists")
            os.replace(target, destination)
        else:
            atomic_write(target, content, item["old_mode"])
    state["state"] = "rolled-back"
    write_state(folder, state)
    return {"state": "rolled-back", "restored_files": len(restore), "new_files_archived": True}


def rollback(folder: Path, expected_sha: str) -> dict:
    folder = folder.expanduser().absolute()
    load_plan(folder, expected_sha)
    lock = regular_path(folder / "transaction.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SetupError("Transaction still running; rollback refused") from exc
    os.close(fd)
    try:
        return _rollback_unlocked(folder, expected_sha)
    finally:
        lock.unlink(missing_ok=True)


def doctor(vault: Path, home: Path) -> dict:
    info = inventory(vault, home)
    # Login status is intentionally queried only on request, never while making a plan.
    login = "not-checked"
    codex = info["binaries"]["codex"]
    if codex and home.expanduser().resolve() == Path.home().resolve():
        try:
            run = subprocess.run([codex, "login", "status"], capture_output=True, timeout=15)
            login = "authenticated" if run.returncode == 0 else "login-required"
        except (OSError, subprocess.TimeoutExpired):
            login = "check-failed"
    return {"inventory": info, "codex_login": login, "runtime_test": "pending-user-session",
            "mcp_tool_tests": "not-run", "note": "Installed/configured/authenticated does not mean functionally tested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "plan", "doctor"):
        p = sub.add_parser(name)
        p.add_argument("--vault", type=Path, required=True)
        p.add_argument("--home", type=Path, default=Path.home())
        if name == "plan":
            p.add_argument("--mode", choices=("codex", "claude-only"), default="codex")
            p.add_argument("--agent", action="append", default=[])
            p.add_argument("--skill", action="append", default=[])
            p.add_argument("--mcp", action="append", default=[])
            p.add_argument("--output", type=Path, required=True)
    for name in ("apply", "rollback"):
        p = sub.add_parser(name)
        p.add_argument("--plan", type=Path, required=True)
        p.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inventory(args.vault, args.home)
        elif args.command == "plan":
            result = stage(make_plan(args.vault, args.home, args.mode, args.agent, args.skill, args.mcp), args.output)
        elif args.command == "doctor":
            result = doctor(args.vault, args.home)
        elif args.command == "apply":
            result = apply(args.plan, args.sha256)
        else:
            result = rollback(args.plan, args.sha256)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (SetupError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
