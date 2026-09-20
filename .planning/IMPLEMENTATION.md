# Community Codex-Erweiterung

Autorisiert am 09.09.2026. Separate Arbeitskopie, keine Änderungen oder Reloads am laufenden privaten Agentic OS des Erstellers. Öffentliches Repo `sebaskauf/agentic-os-codex-addon`.

## 0.2.0 (20.09.2026)

Ziel: Windows-Unterstützung, gemeinsames Gedächtnis mit Claude, Bestandsaufnahme und ein Beweislauf, den Mitglieder selbst fahren.

- [x] Windows-Host: node-pty-Prebuilds `win32-x64` und `win32-arm64` aus dem öffentlichen Agentic-OS-Plugin v0.2.2 samt ConPTY-Patch `windowsConoutConnection.js` nach `host/native/` übernommen. Linux bleibt ohne Prozessstart.
- [x] Bridge (`host/src/codexBridge.ts`): Loopback-WebSocket mit Capability-Token für Windows (`--listen`/`--remote`, 401 ohne Token), Unix-Sockets auf macOS unverändert, `AGENTIC_OS_CODEX_TRANSPORT=ws|unix` zum Erzwingen, `taskkill /t` zum Beenden.
- [x] Binärsuche (`host/src/platform.ts`): `codex.exe` über PATH, `%APPDATA%\npm` und npm-Paketlayout; `CODEX_BIN` und `CODEX_CLI_PATH`; `.cmd`-Shims über `cmd.exe /d /s /c`, Anführungszeichen in Argumenten abgelehnt.
- [x] Installer `scripts/setup.py` 0.2.0: `discover --home`, erweitertes `inspect` (`config_dir`, `brain`, `mcps`, `codex_version`, `host_native_available`), `plan --brain`/`--no-brain` mit verwaltetem AGENTS.md-Block und `[projects]`/`[sandbox_workspace_write]` in `config.toml`, `doctor` mit `brain_link` und `companion_enabled`, `icacls` unter Windows, Plattform-Gates macOS und Windows.
- [x] `integrations/planner.agents_md_block()` für den AGENTS.md-Text.
- [x] `scripts/package.py`: Scan auf Windows-Profilpfade, ZIP-Zeitstempel 2026-09-20.
- [x] Tests grün auf macOS: Host 10, Installer 19, Planner 15 (44). Neu: `.cmd`-Wrapping, kompletter WebSocket-Pfad mit Token, Windows-Plan, Brain außerhalb des Vaults, AGENTS.md-Erhalt und Rollback, `discover`, MCP-Namen ohne Secrets, umbenannter Config-Ordner.
- [x] `SETUP-PROMPT.md` mit Bestandsaufnahme, Plan, Anwenden, Obsidian, Beweislauf (Schritt 7) und Abschluss.
- [x] Doku: `host/README.md`, `docs/RELEASE-NOTES.md`, `docs/VERIFICATION.md`, `.planning/RELEASE-RECORD.json`.
- [x] `README.md` und `INSTALL.md` auf 0.2.0 (fertig 20.09.).

Offen nach 0.2.0:

- [ ] Erster Lauf auf einem echten Windows-Rechner (ConPTY in Obsidian, `codex.exe`-Suche, `taskkill /t`, `icacls`). Abschlussbericht aus SETUP-PROMPT Schritt 8 einsammeln.
- [ ] Intel-Mac-Ausführung.
- [ ] Obsidian-Abnahme durch Mitglieder über den Beweislauf; erst danach `mac_native_obsidian_acceptance` im Release-Record auf `passed`.
- [ ] Nach dem GitHub-Release `code_commit` und `sha256` im Release-Record eintragen.
- [ ] MCP-Anmeldung und Leseaufruf mit Member-Konto.
- Linux bleibt bewusst ohne Prozessstart.

## 0.1.0-pilot.1 (09.09.2026)

- [x] Portable optionale Host-Integration aus bewährtem Code extrahieren, Claude bleibt Standard. Companion statt Überschreiben des privaten Dashboard-Baums.
- [x] Read-only Diagnose mit Fingerprints und explizitem Vault-/Home-Kontext.
- [x] Konkreten Plan und Stage-Paket mit Backups, Drift-Prüfung, idempotentem Apply und selektivem Rollback bauen.
- [x] Rollen-/Skill-Übernahme und explizit ausgewählte MCP-Rezepte mit separaten Login-Schritten implementieren.
- [x] Claude-/Codex-Setup-Skill, README, Einstiegsprompt und Community-Lektion schreiben.
- [x] Frische und existierende Fixture-Installationen, Fork-Konflikt, Rollback, Claude-only, Auth-Status, Pfad-/Symlink-Grenzen prüfen.
- [x] Host-Build und Browser-Vorschau des echten Bundles isoliert geprüft. Native Obsidian-Abnahme blieb offen.
- [x] Paket auf persönliche Daten geprüft, Git-Commit und Remote erstellt, Status und offene Plattform-/Fremdtests dokumentiert.

## Verträge

Installer-Kern unter scripts/ und tests/ gehört Root. Host-Code, Baselines, Host-Build und Host-Tests unter host/ gehören Host-Worker. Portable Provider-Konfiguration, Agenten und MCP-Rezepte unter integrations/ mit eigenen Tests gehören Integrations-Worker. Keine Worker-Änderungen an fremden Bereichen.

Seit 0.2.0 sind macOS und Windows für die ausführende Codex-Host-Einrichtung freigegeben. Linux darf inspizieren, aber keinen Host installieren. Keine fremden Konfigurationen oder persönlichen Rollen als Paketinhalt. Keine Secrets kopieren. Bestehende Member-Anpassungen nicht blind überschreiben. Der verwaltete AGENTS.md-Block ist hash-geschützt, eigener Text bleibt erhalten. Ein vorhandener Config-Eintrag ist kein erfolgreicher Tool-Test.

## Umsetzungsentscheidung

Der private ChatDrawer hängt von großen Teilen des persönlichen Dashboards des Erstellers ab. Die Erweiterung ist deshalb ein eigenständiges Obsidian-Companion-Plugin. Das vermeidet das Überschreiben beliebiger Member-Forks, stellt aber keine Provider-Umschaltung im vorhandenen ChatDrawer bereit. Die Abgrenzung ist in README, INSTALL und Lektionstext sichtbar. Quellcode unter host/ gehört vollständig zu diesem Repo.
