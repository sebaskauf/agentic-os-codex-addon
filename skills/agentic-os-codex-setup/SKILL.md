---
name: agentic-os-codex-setup
description: Set up the optional Codex companion for an existing Obsidian Agentic OS on macOS or Windows and link Codex to the member's shared memory (Second Brain). Use when a member wants Codex alongside Claude, or needs to diagnose, update or roll back this extension. Preserve custom Agentic OS installations, existing AGENTS.md text and selected role prompts.
---

# Agentic OS Codex Setup

Read `../../SETUP-PROMPT.md` and `../../INSTALL.md` from this skill directory, then follow the numbered steps of the setup prompt in the member's language. The repository root is two directories above this SKILL.md. Do not assume the current working directory is the repository or the member's vault.

Explain the actual scope: a separate Codex pane in Obsidian next to the existing Agentic OS, sharing the same memory as Claude through a managed block in the vault's `AGENTS.md` and a trusted-project entry in the Codex configuration. It does not replace the member's chat drawer, cutter cockpit or dashboard. Claude-only members do not need to install anything.

Use the packaged scripts for every file change: `discover`, then `inspect`, then `plan` for the explicitly chosen agent, skill and MCP names (add `--brain` when the Second Brain lives outside the vault, `--no-brain` only when the member declines shared memory), review statuses and affected paths, then `apply` with that exact manifest hash, then `doctor`. Ask for a missing vault choice or an ambiguous account; do not ask again for routine actions already authorized. Stage directories contain configuration snapshots and must remain private.

Windows: work in PowerShell, one command per line, `python` or `py -3` instead of `python3`. Do not turn a failed plan into an ad-hoc overwrite. Never copy credentials between applications, never show configuration files in full, never publish a member's source or configuration.

Guide the member through official Codex installation and `codex login`, and through MCP OAuth. Never collect passwords or tokens in chat. If this session cannot open the member's native login flow, provide the exact local command and wait for its result.

After enabling the companion, run the proof from step 7 of the setup prompt inside the real Codex pane: Codex names and quotes the memory index, Codex writes a test entry that Claude then reads, and "Sitzung fortsetzen" resumes the same thread. Until the member confirms each proof, report it as pending. Do not run paid model tests only to fill a checklist.

Return the install directory, plan/rollback path, completed proofs, remaining login/tool tests and any unsupported platform. A successful configuration write is not proof of a working setup.
