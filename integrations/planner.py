"""Offline, opt-in integration proposals. The caller owns all disk mutations.

Python 3.11+. No subprocesses, authentication, network, or environment reads.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import stat
import tomllib
from urllib.parse import urlsplit

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]*\Z")
BEGIN = "# BEGIN AGENTIC OS CODEX ADDON INTEGRATIONS"
END = "# END AGENTIC OS CODEX ADDON INTEGRATIONS"
RECIPES = {
    "notion": "https://mcp.notion.com/mcp",
    "linear": "https://mcp.linear.app/mcp",
}

class IntegrationError(ValueError):
    """A proposal cannot be produced without ambiguous or unsafe changes."""


def _safe(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise IntegrationError("Paths must be absolute and must not contain traversal")
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise IntegrationError(f"Symlink is not eligible for automatic migration: {parent}")
    return path


def _read(path: Path) -> bytes | None:
    _safe(path)
    if not path.exists():
        return None
    if not path.is_file():
        raise IntegrationError(f"Expected regular file: {path}")
    return path.read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IntegrationError("Configuration must be UTF-8") from exc


def _toml(data: str) -> dict:
    try:
        return tomllib.loads(data)
    except tomllib.TOMLDecodeError as exc:
        # Parser details may contain confidential configuration values.
        raise IntegrationError("Invalid or conflicting TOML configuration") from exc


def _json(data: bytes) -> dict:
    try:
        parsed = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrationError("Invalid JSON configuration") from exc
    if not isinstance(parsed, dict):
        raise IntegrationError("Expected a JSON object")
    return parsed


def _source(paths: list[Path], kind: str, name: str) -> Path:
    found = []
    for path in paths:
        _safe(path)
        if path.exists():
            found.append(path)
    if not found:
        raise IntegrationError(f"Selected {kind} not found: {name}")
    if len(found) > 1:
        raise IntegrationError(f"Selected {kind} exists in both user and project scope: {name}")
    return found[0]


def _role(data: bytes, name: str) -> tuple[str, str]:
    text = _text(data)
    # Keep the entire prompt body byte-for-byte, including CRLF and whitespace.
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n)(.*)\Z", text, re.S)
    if not match:
        raise IntegrationError(f"Agent requires flat YAML frontmatter: {name}")
    meta = {}
    for line in match[1].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        field = re.match(r"([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)\Z", line)
        if not field or field[1] in meta or field[2] in {"|", ">", "|-", ">-"}:
            raise IntegrationError(f"Unsupported agent frontmatter, review manually: {name}")
        value = field[2].strip()
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise IntegrationError(f"Invalid quoted frontmatter: {name}") from exc
        elif value.startswith("'"):
            if not value.endswith("'") or len(value) < 2:
                raise IntegrationError(f"Invalid quoted frontmatter: {name}")
            value = value[1:-1].replace("''", "'")
        meta[field[1]] = value
    if meta.get("name", name) != name:
        raise IntegrationError(f"Agent filename and declared name differ: {name}")
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip() or not match[2].strip():
        raise IntegrationError(f"Agent needs description and prompt body: {name}")
    return description, match[2]


def build_changes(home: Path, vault: Path, selected_agents: list[str],
                  selected_skills: list[str], selected_mcps: list[str]) -> dict:
    """Return changes containing path, before bytes/None, after bytes, and kind.

    Existing role bodies remain unchanged. Managed blocks are hash-guarded,
    unrelated fields stay byte-identical. Selecting fewer items never removes
    an installed integration. Existing unowned collisions require manual review.
    Config snapshots can contain the user's existing credentials; callers MUST
    store plans privately and must never publish them or log before/after bytes.
    """
    home, vault = _safe(home), _safe(vault)
    for names in (selected_agents, selected_skills, selected_mcps):
        if not isinstance(names, list):
            raise IntegrationError("Selections must be unique lists")
        if any(not isinstance(name, str) or not NAME.fullmatch(name) for name in names):
            raise IntegrationError("Invalid integration name")
        if len(names) != len(set(names)):
            raise IntegrationError("Selections must be unique lists")
    changes, statuses, manual = [], [], []
    codex = home / ".codex"
    state_path = codex / "agentic-os-addon-integrations.json"
    state_before = _read(state_path)
    state = _json(state_before) if state_before else {"schema": 1, "blocks": {}}
    if state.get("schema") != 1 or not isinstance(state.get("blocks"), dict):
        raise IntegrationError("Unknown integration ownership state")
    blocks = dict(state["blocks"])

    def propose(path: Path, after: bytes, kind: str, mode: int | None = None) -> None:
        before = _read(path)
        if before != after:
            change = {"path": str(path), "before": before, "after": after, "kind": kind}
            if mode is not None:
                change["mode"] = mode
            changes.append(change)

    def manage(path: Path, additions: dict[str, str], kind: str) -> None:
        """Manage named blocks through a single checksum-protected envelope."""
        relative = str(path.relative_to(codex))
        before = _read(path)
        text = _text(before) if before is not None else ""
        _toml(text)
        old = blocks.get(relative)
        if text.count(BEGIN) != text.count(END) or text.count(BEGIN) > 1:
            raise IntegrationError(f"Invalid managed markers: {relative}")
        owned = {}
        if BEGIN in text:
            start, stop = text.index(BEGIN), text.index(END) + len(END)
            if stop < start or not isinstance(old, dict):
                raise IntegrationError(f"Missing ownership record: {relative}")
            if _sha(text[start:stop].encode()) != old.get("sha256"):
                raise IntegrationError(f"Managed configuration edited, review required: {relative}")
            owned = old.get("entries", {})
            if not isinstance(owned, dict):
                raise IntegrationError("Invalid ownership entries")
            prefix, suffix = text[:start], text[stop:]
        else:
            if old:
                raise IntegrationError(f"Managed configuration removed, review required: {relative}")
            # Profiles use root keys. Global config uses table blocks at the end.
            prefix, suffix = (text + ("\n" if text and not text.endswith("\n") else ""), "\n") if kind == "codex-config" else ("", "\n" + text)
        owned = {**owned, **additions}
        envelope = BEGIN + "\n" + "\n".join(owned[key].rstrip("\n") for key in sorted(owned)) + "\n" + END
        result = prefix + envelope + suffix
        _toml(result)  # Duplicate preexisting fields/tables fail, never overwrite.
        blocks[relative] = {"sha256": _sha(envelope.encode()), "entries": owned}
        propose(path, result.encode(), kind)

    config_entries = {}
    for name in selected_agents:
        source = _source([vault / ".claude/agents" / f"{name}.md", home / ".claude/agents" / f"{name}.md"], "agent", name)
        description, body = _role(_read(source), name)
        quote = lambda value: json.dumps(value, ensure_ascii=False)
        instructions = f"developer_instructions = {quote(body)}\n"
        manage(codex / f"{name}.config.toml", {"role": instructions}, "agent-profile")
        agent_file = codex / "agents" / f"{name}.toml"
        manage(agent_file, {"role": f"name = {quote(name)}\ndescription = {quote(description)}\n" + instructions}, "subagent")
        config_entries[f"agent-{name}"] = f"[agents.{quote(name)}]\ndescription = {quote(description)}\nconfig_file = {quote(str(agent_file))}\n"
        statuses.append({"kind": "agent", "name": name, "state": "planned", "detail": "Exact role prompt preserved. Tools, skills and live role execution remain unverified."})

    for name in selected_skills:
        target = vault / ".agents/skills" / name
        _safe(target)
        if target.exists():
            if not target.is_dir() or not _read(target / "SKILL.md"):
                raise IntegrationError(f"Existing skill has no regular SKILL.md: {name}")
            for entry in target.rglob("*"):
                _safe(entry)
            statuses.append({"kind": "skill", "name": name, "state": "existing", "detail": "Existing project .agents/skills location reused unchanged; skill execution not tested."})
            continue
        source = _source([vault / ".claude/skills" / name, home / ".claude/skills" / name], "skill", name)
        if not source.is_dir() or not _read(source / "SKILL.md"):
            raise IntegrationError(f"Skill requires SKILL.md: {name}")
        for entry in sorted(source.rglob("*")):
            _safe(entry)
            if entry.is_dir():
                continue
            data = _read(entry)
            if data is None:
                raise IntegrationError(f"Skill changed during scan: {name}")
            # Copy only a conservative reusable skill bundle, never secret stores.
            if entry.name.startswith(".") or any(part.startswith(".") for part in entry.relative_to(source).parts):
                raise IntegrationError(f"Hidden skill files require manual review: {name}")
            propose(target / entry.relative_to(source), data, "skill", stat.S_IMODE(entry.stat().st_mode) & 0o777)
        statuses.append({"kind": "skill", "name": name, "state": "planned", "detail": "Skill files copied to project .agents/skills. Instructions preserved; dependencies and live execution unverified."})

    if selected_mcps:
        available = {}
        for path in [home / ".claude.json", vault / ".mcp.json"]:
            data = _read(path)
            if data is None:
                continue
            servers = _json(data).get("mcpServers", {})
            if not isinstance(servers, dict):
                raise IntegrationError("Invalid MCP server map")
            for name in selected_mcps:
                if name in servers:
                    if name in available and available[name] != servers[name]:
                        raise IntegrationError(f"MCP exists with different user/project definitions: {name}")
                    available[name] = servers[name]
        for name in selected_mcps:
            spec = available.get(name)
            if spec is None and name in RECIPES:
                spec = {"url": RECIPES[name]}
            if not isinstance(spec, dict):
                statuses.append({"kind": "mcp", "name": name, "state": "manual-setup", "detail": "No supported selected source or recipe. No changes planned."})
                manual.append(f"Configure {name} using its official Codex instructions, then authenticate and test an appropriate read-only tool.")
                continue
            # Arbitrary subprocess commands, interpolated args, HTTP headers and
            # environment values may contain credentials. Never migrate them.
            forbidden = set(spec) - {"url", "type", "bearer_token_env_var"}
            url = spec.get("url", "")
            try:
                parts = urlsplit(url) if isinstance(url, str) else None
            except ValueError:
                parts = None
            safe_url = bool(parts and parts.scheme == "https" and parts.hostname and not parts.username and not parts.password and not parts.query and not parts.fragment and not any(ch.isspace() for ch in url))
            if forbidden or not safe_url or spec.get("type", "http") not in {"http", "sse"}:
                statuses.append({"kind": "mcp", "name": name, "state": "manual-setup", "detail": "Source contains unsupported settings or possible credentials; nothing copied."})
                manual.append(f"Recreate {name} from its official instructions without exporting credentials. Authenticate locally and perform a read-only tool test.")
                continue
            env_ref = spec.get("bearer_token_env_var")
            if env_ref is not None and (not isinstance(env_ref, str) or not ENV_NAME.fullmatch(env_ref)):
                raise IntegrationError(f"Invalid token environment variable reference: {name}")
            # Generic paths can themselves hold secret tokens. Only recognized
            # conventional MCP endpoint paths are eligible for automatic import.
            if parts.path not in {"", "/", "/mcp", "/sse"}:
                statuses.append({"kind": "mcp", "name": name, "state": "manual-setup", "detail": "Nonstandard endpoint path requires manual credential review."})
                manual.append(f"Review the endpoint for {name} locally; do not paste secret URLs into the setup report.")
                continue
            current_config = _read(codex / "config.toml")
            configured = _toml(_text(current_config)).get("mcp_servers", {}) if current_config else {}
            owned_entries = blocks.get("config.toml", {}).get("entries", {})
            if name in configured and f"mcp-{name}" not in owned_entries:
                existing = configured[name]
                if not isinstance(existing, dict) or existing.get("url") != url or existing.get("bearer_token_env_var") != env_ref:
                    raise IntegrationError(f"Existing Codex MCP differs, review required: {name}")
                state_name = "existing-disabled" if existing.get("enabled") is False else "existing"
                statuses.append({"kind": "mcp", "name": name, "state": state_name, "detail": "Existing Codex connection reused unchanged. Authentication and tool availability unverified."})
                manual.append(f"Check the existing {name} connection and intended account in Codex. Preserve its enabled setting and verify a read-only tool before claiming it works.")
                continue
            block = f"[mcp_servers.{json.dumps(name)}]\nurl = {json.dumps(url)}\n"
            if env_ref:
                block += f"bearer_token_env_var = {json.dumps(env_ref)}\n"
            config_entries[f"mcp-{name}"] = block
            statuses.append({"kind": "mcp", "name": name, "state": "auth-pending", "detail": "Configuration proposed only. Authentication and actual tool availability have not been tested."})
            manual.append(f"After applying, authenticate {name} with `codex mcp login {name}` if the server supports OAuth, or supply its referenced environment variable locally. Then verify a read-only tool in the embedded Codex session.")

    if config_entries:
        manage(codex / "config.toml", config_entries, "codex-config")
    if blocks != state["blocks"]:
        propose(state_path, (json.dumps({"schema": 1, "blocks": blocks}, ensure_ascii=False, indent=2) + "\n").encode(), "integration-ownership")
    return {"changes": changes, "statuses": statuses, "manual_steps": manual}
