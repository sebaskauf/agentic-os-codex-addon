# Optionaler Codex-Host für Agentic OS

Version 0.1.0 ist ein eigenes Obsidian-Plugin neben dem bestehenden Agentic OS. Es verändert keine Dateien des Hauptplugins und startet beim Laden oder Wiederherstellen eines Fensters keinen Prozess. Erst der Klick auf „Codex starten“ öffnet den nativen Codex-Terminalclient. Die Installation allein aktiviert auch keine Obsidian-Community-Plugins.

## Funktionsumfang

Das Plugin stellt einen eigenen Codex-Terminaltab mit Rollenprofil-Auswahl, Arbeitsordner, Stoppen und Wiederaufnahme einer nativ bestätigten Sitzung bereit. Wenn das bestehende Agentic OS den Befehl `agentic-os:open-terminal-pane` registriert, öffnet „Claude in Agentic OS“ dessen bestehendes Claude-Terminal. Fehlt dieser Befehl, bleibt der Button deaktiviert und die Oberfläche erklärt die eingeschränkte Verbindung.

Der Provider-Wechsel findet in v0.1 über getrennte Tabs statt. Dies ist keine Integration in den bestehenden ChatDrawer, keine Kopie von Sebastians Dashboard und keine automatische Anpassung eigener Dashboard-Komponenten. Standard- und Fork-Installationen bleiben unverändert. Ein späterer Adapter kann den öffentlichen Befehl `agentic-os-codex:open-terminal` aufrufen.

Die Rollenliste stammt aus `CODEX_HOME/NAME.config.toml`, standardmäßig `~/.codex`. Der Host startet `codex -p NAME` und übergibt dieselben TOML-Werte an den eigenen App-Server, da dieser kein `-p` besitzt. Der Setup-Planer im übergeordneten Paket erzeugt diese Profile aus den ausdrücklich ausgewählten Rollen. Ein solches Hauptrollenprofil ist von einer nativen Codex-Subagent-Registrierung zu unterscheiden.

Berechtigungen, Modelle und MCPs stammen aus der eigenen Codex-Konfiguration. Das Plugin vergibt keine weiteren Arbeitsordner, kopiert keine Konten und setzt keinen unbeschränkten Modus. Sitzungseinträge enthalten nur Ordner, Profil und eine bestätigte native Thread-ID. Es werden keine Chattexte aufgezeichnet. Leere, noch nicht durch einen User-Turn persistierte Threads werden nicht als wiederaufnehmbar angeboten.

## Installation und Build

Im Ordner `host` ausführen.

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
```

Der Build schreibt ausschließlich nach `host/build`. Der übergeordnete Installer übernimmt den gesamten Inhalt in den neuen Vault-Ordner `.obsidian/plugins/agentic-os-codex`. Er ersetzt keine Agentic-OS-Quelldateien. Der enthaltene `build-manifest.json` dokumentiert SHA-256, Größe und Dateimodus für alle anderen Build-Dateien.

Obsidian anschließend öffnen, das neue Plugin bewusst aktivieren und den Befehl „Agentic OS Codex · Codex-Terminal öffnen“ ausführen. Dann Arbeitsordner und optionales Rollenprofil wählen und starten. Die interne Eigenschaft `enabled` ist lediglich der gespeicherte Hinweis, dass das Mitglied schon einmal eine Sitzung gestartet hat. Sie ist keine zweite Freischaltung und startet keine Prozesse.

Codex muss lokal installiert und angemeldet sein. `CODEX_BIN` kann einen abweichenden Binärpfad festlegen. Die Binärsuche ergänzt typische Benutzer- und Homebrew-Pfade. Das Paket bündelt `node-pty` 1.1.0 für `darwin-arm64` und `darwin-x64`; es wird kein natives Paket aus dem bestehenden Agentic OS geladen. Fehlende native Dateien führen zu einer sichtbaren Fehlermeldung.

## Verifiziert und noch offen

Am 9. September 2026 bestanden TypeScript-Build und acht Tests. Die Prüfungen decken Rollenübergabe, unveränderte Berechtigungen, sichere Thread-Zuordnung, ungültige gespeicherte IDs, leere Threads, einen echten `printf`-Aufruf durch das gebündelte ARM64-PTY sowie den Start des echten lokalen Codex-App-Servers mit isoliertem `CODEX_HOME` und privaten Sockets ab. Es wurde kein Modellturn gestartet.

Die tatsächliche Oberfläche des Build-Bundles wurde im Browser mit simulierten Obsidian-APIs gerendert und manuell betrachtet. Rollenwahl funktioniert; Screenshot liegt unter `test/ui-preview.png`. Die Vorschau lässt sich aus `host` mit `python3 -m http.server 8937 --bind 127.0.0.1` starten und unter `/test/preview.html` öffnen.

Eine separate Obsidian-Instanz mit Testvault und eigenem User-Data-Verzeichnis wurde vorbereitet. Der gestartete Obsidian-Prozess beendete sich sofort; die UI-Steuerung fand nur das produktive Fenster. Dort wurde nichts bedient. Eine erfolgreiche native Obsidian-Abnahme ist damit noch nicht belegt. Ebenfalls offen sind Intel-Mac-Ausführung, ein vollständiger Modellturn, Wiederaufnahme nach echtem Obsidian-Neustart und memberbezogene OAuth/MCP-Funktionstests.

Diese Pilotversion sperrt Prozessstarts unter Windows und Linux. Die übernommene Identitätsbridge benötigt Unix-Sockets. Windows-Unterstützung des ursprünglichen Agentic OS sagt nichts über diese Erweiterung aus.

## Herkunft und Lizenzen

`codexBridge.ts`, `codexProfile.ts`, `sessionIdentity.ts` und `providers/` wurden aus der bereits lokal getesteten Agentic-OS-Codex-Integration übernommen. `platform.ts`, Zustand und UI sind portable Implementierungen dieses Pakets. Keine persönliche Konfiguration, kein Dashboard-Datensatz und keine privaten Arbeitsordner werden ausgeliefert.

`src/vendor/smol-toml` enthält smol-toml 1.8.0 einschließlich BSD-3-Clause-Lizenz und Paketmetadaten. `native` enthält die node-pty-1.1.0-Paketdateien und macOS-Prebuilds aus derselben Integration sowie `LICENSE-node-pty`. Der Build bündelt xterm 6.0.0 und addon-fit 0.11.0 unter MIT. Deren Lizenzdateien werden im Build mitgeliefert. Release-Artefakte sollten nur aus diesem gepinnten Build veröffentlicht werden.
