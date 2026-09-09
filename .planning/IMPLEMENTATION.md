# Community Codex-Erweiterung

Autorisiert am 09.09.2026. Separate Arbeitskopie, keine Änderungen oder Reloads an Sebastians laufendem Agentic OS. Private GitHub-Auslieferung erst nach Paketprüfung. Öffentliche Freigabe erst nach realer Fremd-Abnahme.

## Arbeitsplan

- [x] Portable optionale Host-Integration aus bewährtem Code extrahieren, Claude bleibt Standard. Companion statt Überschreiben des privaten Dashboard-Baums.
- [x] Read-only Diagnose mit Fingerprints und explizitem Vault-/Home-Kontext.
- [x] Konkreten Plan und Stage-Paket mit Backups, Drift-Prüfung, idempotentem Apply und selektivem Rollback bauen.
- [x] Rollen-/Skill-Übernahme und explizit ausgewählte MCP-Rezepte mit separaten Login-Schritten implementieren.
- [x] Claude-/Codex-Setup-Skill, README, Einstiegsprompt und Community-Lektion schreiben.
- [x] Frische und existierende Fixture-Installationen, Fork-Konflikt, Rollback, Claude-only, Auth-Status, Pfad-/Symlink-Grenzen prüfen.
- [x] Host-Build und Browser-Vorschau des echten Bundles isoliert geprüft. Native Obsidian-Abnahme noch offen, siehe docs/VERIFICATION.md.
- [ ] Paket auf persönliche Daten prüfen, Git-Commit und privates Remote erstellen, Status und offene Plattform-/Fremdtests dokumentieren.

## Verträge

Installer-Kern unter scripts/ und tests/ gehört Root. Host-Code, Baselines, Host-Build und Host-Tests unter host/ gehören Host-Worker. Portable Provider-Konfiguration, Agenten und MCP-Rezepte unter integrations/ mit eigenen Tests gehören Integrations-Worker. Keine Worker-Änderungen an fremden Bereichen.

Nur macOS für ausführende Codex-Host-Einrichtung freigeben. Windows-Diagnose darf laufen, aber keinen nicht unterstützten Host installieren. Keine fremden Konfigurationen oder persönlichen Rollen als Paketinhalt. Keine Secrets kopieren. Bestehende Member-Anpassungen nicht blind überschreiben. Ein vorhandener Config-Eintrag ist kein erfolgreicher Tool-Test.

## Umsetzungsentscheidung

Der private ChatDrawer hängt von großen Teilen des persönlichen Dashboards ab. v0.1 wird deshalb als eigenständiges Obsidian-Companion-Plugin umgesetzt. Dies vermeidet das Überschreiben beliebiger Member-Forks, stellt aber noch keine gleiche Provider-Umschaltung im vorhandenen ChatDrawer bereit. Die Abgrenzung wurde während der Umsetzung kommuniziert und ist in README, INSTALL und Lektionstext sichtbar. Quellcode unter host/ gehört vollständig zum neuen Repo.
