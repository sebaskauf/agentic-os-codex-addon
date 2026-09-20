# Codex-Host für Agentic OS

`host/` ist das Obsidian-Companion-Plugin `agentic-os-codex`, Version 0.2.0. Es läuft neben deinem bestehenden Agentic OS, verändert keine Datei des Hauptplugins und startet beim Laden oder Wiederherstellen eines Fensters keinen Prozess. Erst der Klick auf „Codex starten“ öffnet den nativen Codex-Terminalclient. Die Installation allein aktiviert das Plugin nicht.

## Funktionsumfang

Ein eigener Codex-Terminaltab mit Leiste: Claude-Button, Profil-Auswahl, Arbeitsordner, „Codex starten“, „Stoppen“ und „Sitzung fortsetzen“. Der Claude-Button öffnet das Terminal des bestehenden Agentic OS, wenn dessen Befehl `agentic-os:open-terminal-pane` registriert ist; fehlt er, bleibt der Button deaktiviert. Der Provider-Wechsel läuft über getrennte Tabs, nicht im Chat-Drawer des Hauptplugins. Ein späterer Adapter kann den öffentlichen Befehl `agentic-os-codex:open-terminal` aufrufen.

Die Profilliste stammt aus `CODEX_HOME/NAME.config.toml`, Standard `~/.codex`. Der Host startet `codex -p NAME` und übergibt dieselben TOML-Werte an den App-Server, der selbst kein `-p` kennt. Der Setup-Planer im übergeordneten Paket erzeugt diese Profile aus den ausdrücklich ausgewählten Rollen.

Berechtigungen, Modelle und MCPs kommen aus der eigenen Codex-Konfiguration. Das Plugin vergibt keine weiteren Arbeitsordner, kopiert keine Konten und setzt keinen unbeschränkten Modus. Sitzungseinträge enthalten nur Ordner, Profil und eine bestätigte native Thread-ID, keine Chattexte. Leere Threads ohne User-Turn werden nicht zur Wiederaufnahme angeboten.

## Plattformen

| Plattform | Ordner in `host/native/` | Stand 20.09.2026 |
|---|---|---|
| macOS Apple Silicon | `darwin-arm64` | alle Tests grün, Entwicklungsplattform |
| macOS Intel | `darwin-x64` | Prebuild enthalten, Ausführung nicht geprüft |
| Windows x64 | `win32-x64` | Prebuild enthalten, kein Lauf auf echtem Windows-Rechner |
| Windows ARM | `win32-arm64` | Prebuild enthalten, kein Lauf auf echtem Windows-Rechner |
| Linux | keiner | startet keinen Prozess |

Alle vier Ordner enthalten node-pty 1.1.0 (`package.json`, `lib/`, `prebuilds/`), dazu `LICENSE-node-pty`. Die beiden Windows-Ordner stammen aus dem öffentlichen Agentic-OS-Plugin v0.2.2 und enthalten dessen ConPTY-Patch `lib/windowsConoutConnection.js`. Der Patch ist nötig, weil Obsidians Electron-Renderer keine `worker_threads` erlaubt. Es wird kein natives Paket aus dem installierten Agentic OS geladen. Fehlt der Ordner für die eigene Plattform, meldet das Plugin sichtbar „Terminalpaket fehlt“.

## Bridge-Transporte (`src/codexBridge.ts`)

**macOS:** privates Unix-Socket-Paar unter `/tmp/aos-codex-*` (Ordner 0700, Sockets 0600), unverändert seit 0.1.0.

**Windows:** Loopback-WebSocket. Der Host startet den App-Server mit

```
codex app-server --listen ws://127.0.0.1:<Port> --ws-auth capability-token --ws-token-file <privat>
```

Die TUI verbindet über

```
codex --remote ws://127.0.0.1:<Frontport> --remote-auth-token-env AGENTIC_OS_CODEX_TOKEN
```

Das Token wird der TUI nur als Umgebungsvariable übergeben, nie als Argument. Ohne Token antwortet der App-Server mit 401. Prozessende unter Windows über `taskkill /t`.

`AGENTIC_OS_CODEX_TRANSPORT=ws|unix` erzwingt einen Transport unabhängig von der Plattform. Damit wurde der WebSocket-Pfad auf macOS geprüft.

## Binärsuche (`src/platform.ts`)

macOS: `codex` aus PATH plus typische Benutzer- und Homebrew-Pfade. Windows: `codex.exe` aus PATH, `%APPDATA%\npm` und dem npm-Paketlayout `@openai/codex-win32-<arch>`. `CODEX_BIN` und `CODEX_CLI_PATH` überschreiben die Suche. npm-`.cmd`-Shims startet der Host über `cmd.exe /d /s /c`, Pfade mit Leerzeichen werden dabei in Anführungszeichen gesetzt. Argumente, die selbst Anführungszeichen enthalten, lehnt er ab.

## Build

Im Ordner `host`:

```sh
npm ci --ignore-scripts
npm run build
npm test
```

`npm run build` prüft TypeScript (`tsc --noEmit`) und schreibt ausschließlich nach `host/build`: `main.js`, `styles.css`, `manifest.json`, `native/` mit allen vier Ordnern, die Lizenzdateien und `build-manifest.json` (SHA-256, Größe und Dateimodus jeder anderen Build-Datei). Der Installer kopiert `host/build` in den Vault-Ordner `.obsidian/plugins/agentic-os-codex` und ersetzt keine Agentic-OS-Datei. Kein Build-Befehl lädt ein aktives Plugin neu.

Das Release-Asset `agentic-os-codex-addon.zip` enthält `host/build` fertig gebaut. Mitglieder brauchen weder Node noch npm; die Befehle oben gelten nur für den Source-Checkout.

## Tests

`npm test` führt 10 Tests aus, alle grün auf macOS Apple Silicon am 20.09.2026:

1. Frischer Zustand ist opt-in, ohne Session und ohne persönlichen Default.
2. Nicht vertrauenswürdige gespeicherte Identitäten erzeugen keinen Resume-Befehl.
3. Der Start hält sich exakt ans Profil, ohne Rechte oder Arbeitsordner zu erweitern.
4. Nur die korrelierte letzte native Antwort darf einen Thread wählen, keine Hintergrund-Agenten.
5. Ein Observer-Fehler entwertet die vorherige Identität, statt eine alte Sitzung fortzusetzen.
6. Das gebündelte macOS-PTY führt einen harmlosen Befehl aus (nur macOS).
7. Ein echter lokaler Codex-App-Server öffnet private Unix-Sockets, ohne Modellturn (nur macOS).
8. Leere native Threads sind keine dauerhaften Resume-Ziele.
9. Neu: `.cmd`-Shims werden für `cmd.exe` gewrappt, Pfade mit Leerzeichen gequotet, Argumente mit Anführungszeichen abgelehnt. `supportedPlatform()` ist nur auf macOS und Windows wahr.
10. Neu: WebSocket-Bridge mit Capability-Token. Echter App-Server, Token mit 64 Hex-Zeichen nur in der Umgebung, Handshake ohne Token bekommt 401, eine echte TUI über das gebündelte PTY verbindet mit Token und zeigt das Codex-Banner (übersprungen auf Linux).

Die Tests starten keinen Modellturn.

## Grenzen (Stand 20.09.2026)

- Kein Lauf auf einem echten Windows-Rechner. Der WebSocket-Transport wurde auf macOS im Windows-Modus verifiziert; die ConPTY-Prebuilds sind die des öffentlichen Agentic-OS-Plugins.
- Intel-Mac: Prebuild enthalten, nicht ausgeführt.
- Linux: kein Prozessstart.
- Abnahme in der echten Obsidian-Oberfläche: durch die Mitglieder über den Beweislauf in [SETUP-PROMPT.md](../SETUP-PROMPT.md), Schritt 7 (Codex nennt den Gedächtnis-Index, schreibt einen Testeintrag, den Claude liest, Sitzung fortsetzen).
- Codex-CLI-Basis ist 0.155.x (stabil 0.155.1 vom 18.09.2026). Andere Versionen brauchen einen Laufzeittest, vor allem für `app-server`, `--listen` und `--remote`.

## Herkunft und Lizenzen

`codexBridge.ts`, `codexProfile.ts`, `sessionIdentity.ts` und `providers/` stammen aus der lokal getesteten Agentic-OS-Codex-Integration. `platform.ts`, Zustand und UI sind portable Implementierungen dieses Pakets. Keine persönliche Konfiguration, kein Dashboard-Datensatz und keine privaten Arbeitsordner werden ausgeliefert.

`src/vendor/smol-toml` enthält smol-toml 1.8.0 mit BSD-3-Clause-Lizenz und Paketmetadaten. `native/` enthält node-pty 1.1.0 mit Prebuilds für vier Plattformen und `LICENSE-node-pty`. Der Build bündelt xterm 6.0.0 und addon-fit 0.11.0 unter MIT; die Lizenzdateien liegen im Build bei. Release-Artefakte nur aus diesem gepinnten Build veröffentlichen.

Übergeordnet: [README.md](../README.md), [INSTALL.md](../INSTALL.md), [docs/VERIFICATION.md](../docs/VERIFICATION.md).
