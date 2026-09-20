# Agentic OS Codex Erweiterung

Codex als freiwilliger Zusatz zu deinem vorhandenen Agentic OS, auf Mac und Windows. Dein bisheriges Agentic OS und deine Claude-Sessions werden nicht umgebaut. Claude und Codex lesen und schreiben dasselbe Gedächtnis.

Die Erweiterung öffnet eine eigene Codex-Terminalansicht in Obsidian. Dort wählst du deinen Projektordner und eine übernommene Agentenrolle. Über den Claude-Button öffnest du das Terminal des vorhandenen Agentic OS, sofern dessen Standardbefehl vorhanden ist. Eine Umschaltung innerhalb des bisherigen Chat-Drawers und die Erweiterung separater Cutting-Cockpits sind nicht Bestandteil dieser Fassung.

## Einrichtung

Kopier den Setup-Prompt aus [SETUP-PROMPT.md](SETUP-PROMPT.md) in Claude Code oder Codex. Er lädt das Release, macht eine Bestandsaufnahme deines Rechners (Vaults, Second Brain, Claude, Codex, Agents, Skills, MCPs), zeigt dir den Änderungsplan, wendet ihn an, schaltet die Ansicht in Obsidian ein und beweist am Ende, dass beide Agenten dasselbe Gedächtnis benutzen.

Das Release-Paket enthält die gebaute Erweiterung samt Terminaldateien für macOS (Apple Silicon, Intel) und Windows (x64, ARM64). Node.js brauchst du dafür nicht.

Direkt aus dem Quellcode: [INSTALL.md](INSTALL.md).

## Was das Setup übernimmt

- Bestehendes Agentic OS, Second Brain, lokale Rollen, Skills und MCP-Namen erfassen (`discover`, `inspect`).
- Das gemeinsame Gedächtnis verbinden: ein verwalteter Block in `<vault>/AGENTS.md` sagt Codex, wo der Gedächtnis-Index liegt und wie es dort schreibt; dein Vault wird in der Codex-Konfiguration als vertrauenswürdiges Projekt eingetragen. Liegt dein Second Brain außerhalb des Vaults, wird es als zusätzlicher Schreibpfad ergänzt.
- Ausgewählte Rollen mit unverändertem Fachprompt als Codex-Profile bereitstellen.
- Ausgewählte Skills in den Projekt-Skillordner übernehmen.
- Ausgewählte unterstützte MCP-Verbindungen konfigurieren. Notion und Linear sind als OAuth-Rezepte enthalten.
- Alles als geprüften Plan mit Fingerprints, privaten Sicherungen und selektivem Rollback anwenden. Eigene Änderungen und Konflikte werden erkannt und erhalten.

Login und Kontofreigaben erfolgen beim jeweiligen Anbieter. Der Installer ruft keine Modelle auf, erweitert keine globalen Zugriffsrechte über deinen Vault hinaus und kopiert keine Anmeldedateien.

## Voraussetzungen

macOS 13 oder neuer beziehungsweise Windows 10 ab Version 1809 (empfohlen Windows 11), ein vorhandenes Agentic OS in einem lokalen Obsidian-Vault, Python ab 3.11 und ein Codex-CLI-Zugang mit deinem ChatGPT-Konto. Entwickelt gegen Codex CLI 0.155.

Der Codex-Transport läuft auf dem Mac über einen privaten Unix-Socket, unter Windows über einen lokalen WebSocket-Port mit Zufallstoken. Der Windows-Pfad wurde auf dem Mac im Windows-Modus verifiziert und nutzt die Terminaldateien des öffentlichen Agentic-OS-Plugins; ein Lauf auf einem echten Windows-Rechner steht noch aus und ist Teil des Beweislaufs im Setup-Prompt.

## Entwicklung

```sh
cd host
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
cd ..
python3 -B -m unittest discover -s tests -v
python3 -B -m unittest integrations.test_planner -v
python3 scripts/package.py --output .local/agentic-os-codex-addon-0.2.0.zip
```

`host/build` ist ein isoliertes Build-Verzeichnis. Kein Build-Befehl installiert oder lädt ein aktives Obsidian-Plugin neu.

Details: [INSTALL.md](INSTALL.md), [Integrationen](integrations/README.md), [Host](host/README.md), [Abnahme](docs/VERIFICATION.md), [Release-Notes](docs/RELEASE-NOTES.md).
