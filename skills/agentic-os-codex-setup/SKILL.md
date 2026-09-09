---
name: agentic-os-codex-setup
description: Set up the optional Codex companion for an existing Obsidian Agentic OS. Use when a member wants Codex alongside Claude, or needs to diagnose, update or roll back this extension. Preserve custom Agentic OS installations and selected role prompts.
---

# Agentic OS Codex Setup

Read `../../INSTALL.md` from this skill directory, then follow its workflow. The repository root is two directories above this SKILL.md. Do not assume the current working directory is the repository or the member's vault.

Explain the actual scope in the member's language. This version opens a separate Codex pane in Obsidian next to the existing Agentic OS. It does not replace the member's existing chat drawer, cutter cockpit, dashboard or memory system. Claude-only members do not need to install anything.

Use the packaged scripts for file changes. First run inspect, then plan for the explicitly chosen agent, skill and MCP names. Review statuses and the concrete affected files. Apply that exact manifest hash only within the member's requested scope. Ask for missing vault location or an ambiguous account choice; do not ask again for routine actions already authorized. Stage directories contain local configuration snapshots and must remain private.

Do not turn a failed plan into an ad-hoc overwrite. Resolve the identified conflict in a new plan or explain the limitation. Never copy credentials between applications or publish a member's source/configuration. Agent instructions remain unchanged; models, permission rules, tool names and hooks can differ across providers and must be tested separately.

Guide the member through official Codex installation/login and selected MCP OAuth. Never collect passwords or tokens in chat. If this session cannot open the member's native login flow, provide the exact local command and wait for its result. Authentication is not complete merely because a server is listed.

After installation, guide enabling the companion and testing inside its actual Codex pane. Verify role behavior, skill availability and an appropriate read-only call for each selected integration. Until the member supplies evidence, report these as pending. Do not run paid model tests or business operations just to fill a status checklist.

Return the install directory, plan/rollback path, completed checks, remaining login/tool tests and any unsupported platform. A successful build or configuration write is not proof of a complete member setup.
