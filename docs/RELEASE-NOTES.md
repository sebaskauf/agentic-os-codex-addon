# 0.2.0 (20.09.2026)

Zweite Fassung der optionalen Codex-Erweiterung. Neu: Windows, gemeinsames Gedächtnis mit Claude, Bestandsaufnahme per `discover` und ein Beweislauf, den Mitglieder selbst fahren.

## Windows

- Der Host läuft auf macOS und Windows. `host/native/` enthält node-pty-Prebuilds für `darwin-arm64`, `darwin-x64`, `win32-x64` und `win32-arm64`. Die Windows-Ordner stammen aus dem öffentlichen Agentic-OS-Plugin v0.2.2 samt ConPTY-Patch `windowsConoutConnection.js`, weil Obsidians Electron-Renderer keine `worker_threads` erlaubt. Linux startet weiterhin keinen Prozess.
- Bridge: macOS nutzt wie bisher ein privates Unix-Socket-Paar. Windows nutzt einen Loopback-WebSocket mit Capability-Token (`codex app-server --listen ws://127.0.0.1:<Port> --ws-auth capability-token --ws-token-file <privat>`, TUI per `--remote` und `--remote-auth-token-env AGENTIC_OS_CODEX_TOKEN`). Ohne Token antwortet der App-Server mit 401. `AGENTIC_OS_CODEX_TRANSPORT=ws|unix` erzwingt den Transport zum Testen. Prozessende unter Windows über `taskkill /t`.
- Binärsuche findet `codex.exe` (PATH, `%APPDATA%\npm`, npm-Paketlayout `@openai/codex-win32-<arch>`), akzeptiert `CODEX_BIN` und `CODEX_CLI_PATH`, startet npm-`.cmd`-Shims über `cmd.exe /d /s /c` und lehnt Argumente mit Anführungszeichen ab.
- Installer: Plattform-Gates sind jetzt macOS und Windows. Plan-Ordner werden unter Windows per `icacls` auf den Benutzer beschränkt (best effort).

## Gemeinsames Gedächtnis

- `plan` verbindet Codex standardmäßig mit dem Second Brain: ein verwalteter Block (Marker `<!-- BEGIN/END AGENTIC OS CODEX ADDON -->`) am Anfang von `<vault>/AGENTS.md`. Eigener Text bleibt darunter erhalten, der Block ist hash-geschützt, Rollback stellt das Original her. Dazu in `~/.codex/config.toml` der Block `[projects."<vault>"] trust_level = "trusted"`.
- Liegt das Second Brain außerhalb des Vaults: `--brain <Pfad>` ergänzt `[projects."<brain>"]` und `[sandbox_workspace_write] writable_roots = ["<brain>"]`. `--no-brain` lässt das gemeinsame Gedächtnis weg.
- `integrations/planner.agents_md_block()` erzeugt den Text: CLAUDE.md zuerst lesen, `memory/MEMORY.md` ist der Index, neue Einträge als Datei in `memory/` mit Frontmatter `name`, `description`, `metadata.type` plus Indexzeile, keine zweite Kopie, nichts löschen ohne Ja.
- `doctor` meldet zusätzlich `brain_link` (`configured` oder `missing`) und `companion_enabled`.

## Bestandsaufnahme

- Neu `discover --home`: liest Obsidians `obsidian.json` je Plattform, listet Vaults mit den Flags `agentic_os`, `companion`, `claude_md`, `memory_index`, die Binaries `claude`, `codex`, `node`, `npm`, `git`, `python` sowie `codex --version`.
- `inspect` liefert zusätzlich `config_dir` (erkennt umbenannte `.obsidian`-Ordner), `brain` (`claude_md`, `agents_md`, `addon_block`, `memory_index`, `auto_memory_directory`), `mcps` (nur Namen aus `~/.claude.json` und `<vault>/.mcp.json`, keine Schlüssel), `codex_version` und `host_native_available`.

## Beweislauf

- `SETUP-PROMPT.md` im Repo-Root ist der Einstieg für Mitglieder: Bestandsaufnahme, Plan, Anwenden, Obsidian, Beweislauf, Abschluss. Schritt 7 prüft, ob Codex den Gedächtnis-Index nennt, einen Testeintrag schreibt, den Claude anschließend liest, und ob sich die Sitzung fortsetzen lässt. Damit erfolgt die Abnahme in der echten Obsidian-Oberfläche durch die Mitglieder.

## Paket

- Release-Asset `agentic-os-codex-addon.zip` unter `https://github.com/sebaskauf/agentic-os-codex-addon/releases/latest/download/agentic-os-codex-addon.zip`. Enthält `host/build` mit allen vier native-Ordnern; Node ist für Mitglieder nicht nötig.
- `scripts/package.py` erkennt im Textscan jetzt auch Windows-Profilpfade (Laufwerk, Users, Benutzername). ZIP-Zeitstempel 2026-09-20.
- Codex-CLI-Basis 0.155.x (stabil 0.155.1 vom 18.09.2026). Windows nativ in PowerShell; Codex-Installer `irm https://chatgpt.com/codex/install.ps1 | iex` oder `npm install -g @openai/codex`.

## Tests

44 automatisierte Tests grün auf macOS am 20.09.2026: 10 im Host (`npm test`), 19 im Installer (`python3 -B -m unittest discover -s tests`), 15 im Planner (`python3 -B -m unittest integrations.test_planner`). Neu im Host: `.cmd`-Wrapping und der komplette WebSocket-Pfad mit Token (401 ohne Token, echte TUI verbindet mit Token). Neu im Installer: Windows-Plan mit Host und AGENTS.md, Brain außerhalb des Vaults, AGENTS.md erhält Member-Text und ist rückbaubar, `discover` aus `obsidian.json`, MCP-Namen ohne Secrets, umbenannter Config-Ordner. Details in [VERIFICATION.md](VERIFICATION.md).

## Offen

- Kein Lauf auf einem echten Windows-Rechner. Der WebSocket-Transport wurde auf macOS im Windows-Modus verifiziert, die ConPTY-Prebuilds sind die des öffentlichen Agentic-OS-Plugins.
- Intel-Mac nicht ausgeführt, Linux ohne Prozessstart.
- Abnahme in der echten Obsidian-Oberfläche über den Beweislauf der Mitglieder.
- Die direkte Provider-Umschaltung im Chat-Drawer des Hauptplugins ist weiterhin nicht enthalten.

# v0.1.0-pilot.1 (09.09.2026)

Erste private Pilotfassung, nur macOS. Eigenständiges Obsidian-Codex-Terminal mit Profilauswahl, deterministischer Setup-Installer mit Sicherung und Rollback, ausgewählte Agenten-/Skill-Übernahme, Notion-/Linear-OAuth-Rezepte, Setup-Skill für Claude und Codex, vorbereiteter Systeme-Modul-Text. 37 bestandene Prüfungen. Native Obsidian-Abnahme, fremde Kontoverbindungen und Intel-Ausführung standen aus.
