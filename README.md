# Agentic OS Codex Erweiterung

Codex als freiwilliger Zusatz zu deinem vorhandenen Agentic OS. Dein bisheriges Agentic OS und deine Claude-Sessions werden nicht umgebaut.

Die erste Fassung öffnet eine eigene Codex-Terminalansicht in Obsidian. Dort wählst du deinen Projektordner und eine übernommene Agentenrolle. Über den Claude-Button kannst du das Terminal des vorhandenen Agentic OS öffnen, sofern dessen Standardbefehl vorhanden ist. Eine Umschaltung innerhalb des bisherigen Chat-Drawers und die Erweiterung separater Cutting-Cockpits sind nicht Bestandteil dieser Fassung.

Status ist eine Pilotfassung für macOS. Windows wird bei der Installation ausdrücklich abgewiesen. Ein Test auf einem fremden Mitglieder-Rechner und dessen Kontoverbindungen ist vor öffentlicher Freigabe noch erforderlich.

## Einrichtung mit Claude oder Codex

Lade das Release-Paket herunter und entpacke es. Gib deinem Agenten diesen Auftrag und ergänze den tatsächlichen Ordnerpfad.

> Lies die INSTALL.md im entpackten Ordner der Agentic-OS-Codex-Erweiterung. Prüfe mein vorhandenes Agentic OS und richte den optionalen Codex-Zusatz ein. Übernimm die Agenten, Skills und Verbindungen, die ich auswähle. Erhalte meine bisherigen Anpassungen und zeig mir zuerst den konkreten Änderungsplan. Begleite mich bei den nötigen Anmeldungen und prüfe anschließend das Ergebnis.

Das Paket funktioniert als Setup-Anleitung aus beiden Coding-Agenten. Zusätzlich enthält es native Claude- und Codex-Plugin-Manifeste für den Setup-Skill. Eine Marketplace-Installation ist für den Einstiegsprompt nicht nötig und wird durch den Installer nicht im Hintergrund vorgenommen.

## Was das Setup übernimmt

- Bestehendes Agentic OS und lokale Rollen/Skills erfassen.
- Ausgewählte Rollen mit unverändertem Fachprompt für Codex bereitstellen.
- Ausgewählte Skills in den Projekt-Skillordner übernehmen.
- Ausgewählte unterstützte MCP-Verbindungen konfigurieren. Notion und Linear sind als OAuth-Rezepte enthalten.
- Ein konkretes Paket mit Fingerprints, privaten Sicherungen und selektivem Rollback installieren.
- Eigene Veränderungen und Konfigurationskonflikte erkennen und erhalten.

Login und Kontofreigaben erfolgen beim jeweiligen Anbieter. Die Einrichtung unterscheidet vorhandene Konfiguration, Anmeldung und tatsächlichen Tool-Test. Andere MCPs mit eigenen Prozessen, Headern oder Schlüsseln benötigen die passende native Einrichtung. Private Konfigurationen werden nicht mit dem Repository ausgeliefert.

## Voraussetzungen

macOS, ein vorhandenes Agentic OS in einem lokalen Obsidian-Vault, Python ab 3.11 und ein nutzbarer Codex-CLI-Zugang. Das Release enthält die gebaute Obsidian-Erweiterung und ihre nativen Terminaldateien für Apple Silicon und Intel. Der native Terminaltest wurde auf Apple Silicon ausgeführt; Intel bleibt separat zu prüfen.

Die CLI- und MCP-Nutzung unterliegt deinem eigenen Konto. Der Installer selbst ruft keine Modelle auf. Er erweitert keine globalen Zugriffsrechte und kopiert keine Anmeldedateien.

## Entwicklung

```sh
cd host
npm ci
npm run build
npm test
cd ..
python3 -B -m unittest discover -s tests -v
python3 -B -m unittest integrations.test_planner -v
python3 scripts/package.py --output .local/agentic-os-codex-addon-0.1.0.zip
```

`host/build` ist ein isoliertes Build-Verzeichnis. Kein Build-Befehl installiert oder lädt ein aktives Obsidian-Plugin neu. Der Source-Checkout enthält noch kein Build; für Mitglieder ist das vorbereitete Release-Paket der einfachere Weg.

Details stehen in [INSTALL.md](INSTALL.md), [Integrationen](integrations/README.md) und [Abnahme](docs/VERIFICATION.md).
