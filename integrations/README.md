# Integration planner

`planner.py` creates offline proposals using Python 3.11 or newer and the standard library. It does not write files, execute commands, connect accounts or call models. The transaction runner must validate and apply the proposed changes.

```python
from pathlib import Path
from integrations.planner import build_changes

result = build_changes(
    home=Path('/absolute/member/home'),
    vault=Path('/absolute/member/vault'),
    selected_agents=['writer'],
    selected_skills=['research'],
    selected_mcps=['notion'],
)
```

The result contains `changes`, `statuses` and `manual_steps`. Each change contains an absolute `path`, original `before` bytes or `None`, proposed `after` bytes and `kind`. New skill files also include a `mode` with ordinary permission bits, preserving executable scripts without setuid or setgid. Snapshots may contain existing member credentials from their Codex config. Keep plans private and out of Git, do not print their contents, and validate original bytes again during application. The planner itself never exports credentials from Claude MCP definitions.

## Agent roles

Selected roles come from `<vault>/.claude/agents/NAME.md` or `<home>/.claude/agents/NAME.md`. If both exist, installation stops for explicit source selection. The supported flat YAML subset intentionally rejects ambiguous metadata rather than silently dropping it. Prompt text following frontmatter is preserved exactly, including whitespace and CRLF. Metadata for provider-specific models, permissions, tool filters, hooks and memory is not translated. Test those dependencies before claiming parity.

The outputs are `<home>/.codex/NAME.config.toml`, `<home>/.codex/agents/NAME.toml` and entries in `<home>/.codex/config.toml`. The host selects direct profiles with `-p NAME`. No permission or model override is added. Unmanaged fields and comments remain unchanged. Managed blocks have a checksum ownership record. If a member changes a managed block, the next plan fails and requires review. Unowned conflicting keys fail instead of being replaced. Deselecting items does not uninstall them.

## Skills

Existing regular directories under `<vault>/.agents/skills/NAME` are reused without changes. Otherwise, a selected local `.claude/skills/NAME` bundle is copied into that supported project skill location. Nothing is symlinked. Hidden files and symlinks are refused. Executable permission bits of new skill files are preserved. Skills may still depend on native packages. The planner does not install those dependencies or claim scripts run successfully. The setup agent must inspect the selected bundle and perform its smoke test. Do not select bundles containing embedded private data or credentials.

## MCP connections

Only explicitly selected names are considered. Built-in OAuth recipes use official Notion and Linear remote endpoints. Existing definitions are read from project `.mcp.json` and top-level user `.claude.json` `mcpServers`; conflicting definitions stop the plan. Generic imports accept HTTPS endpoints with conventional root, `/mcp` or `/sse` paths, plus an optional named bearer-token environment reference. Commands, arguments, headers, environment values, query strings and secret-bearing path formats are never copied. Those definitions receive a manual setup step instead. The setup does not start any MCP subprocess.

After applying, native `codex mcp login NAME` can initiate OAuth for supporting services. The member chooses and authorizes the correct account. Environment-variable credentials must be supplied locally. Authenticated and tool-tested are separate states. The planner reports `auth-pending`, never live verification. Finish by invoking an appropriate read-only tool from the actual embedded Codex session. Claude, local Codex and hosted app connections may have different credential scopes.

Official recipes checked on 2026-09-09

- [Notion connection documentation](https://developers.notion.com/guides/mcp/get-started-with-mcp)
- [Linear MCP documentation](https://linear.app/docs/mcp)
- [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

## Native migration candidate

The installed Codex app-server schema generated successfully on 2026-09-09 and includes `externalAgentConfig/detect` and `externalAgentConfig/import`. Native migration remains a future adapter candidate. It has not been tested for exact prompt preservation, conflict handling or selective rollback in customized member installations. This release therefore uses narrow deterministic proposals with caller-managed transactions. It does not invoke the native import API or experimental plugin-install RPCs. Relevant [App Server documentation](https://learn.chatgpt.com/docs/app-server).

## Verification

Run from the repository root

```sh
python3 -B -m unittest integrations.test_planner -v
```

Fixture tests cover exact prompts, no mutation, idempotence, unrelated TOML preservation, managed-field conflicts, unowned collisions, no implicit uninstall, traversal and symlink rejection, confidential MCP fields and error-message redaction, conventional remote imports and skill reuse. No account authentication or live model/tool test is implied by these offline checks.

Native profile loading was additionally verified against installed `codex-cli 0.153.4` using an isolated home and Codex home. The CLI help explicitly describes `-p NAME` as layering `<CODEX_HOME>/NAME.config.toml`. A dummy base provider and a different dummy profile provider produce different local configuration errors, proving the native profile file is loaded before model initialization. Both providers intentionally do not exist, so no model or API call can take place. A plain `codex mcp list` did not distinguish the two profiles and is not treated as loader evidence.

```sh
AOS_TEST_NATIVE_CODEX=1 python3 -B -m unittest integrations.test_native_profile -v
```

This is opt-in because it depends on the installed Codex CLI. It verifies configuration-layer selection, not model execution or provider transport. Ordinary fixture coverage includes preserving executable file permissions for new skill scripts.
