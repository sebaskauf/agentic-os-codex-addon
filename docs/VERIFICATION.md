# Abnahmestand 0.2.0

Stand 20.09.2026. Alles Folgende lief auf macOS Apple Silicon. Codex-CLI-Basis 0.155.x. Keine Installation in einem produktiven Vault, kein Modellturn in den automatisierten Tests.

## Was verifiziert wurde

### Host (10 Tests)

```sh
cd host
npm ci --ignore-scripts
npm run build
npm test
```

Ergebnis: 10 Tests grün, TypeScript-Check und isolierter Build bestanden. Abgedeckt wie in 0.1.0: Zustand ohne automatischen Start, keine Rechteausweitung durch Profile, sichere Thread-Zuordnung, ungültige gespeicherte IDs, Observer-Fehler, leere Threads, ein echter harmloser Befehl über das gebündelte ARM64-PTY, ein echter Codex-App-Server mit privaten Unix-Sockets.

Neu in 0.2.0:

- `.cmd`-Wrapping: ein npm-Shim wird zu `cmd.exe /d /s /c "<shim> <args>"`, Pfade mit Leerzeichen gequotet, ein Argument mit Anführungszeichen wirft. `supportedPlatform()` ist nur auf macOS und Windows wahr.
- WebSocket-Pfad mit Token: mit `AGENTIC_OS_CODEX_TRANSPORT=ws` startet die Bridge einen echten `codex app-server --listen ws://127.0.0.1:<Port>` mit Capability-Token. Das Token (64 Hex-Zeichen) liegt nur in der Umgebung der TUI, die Argumente enthalten nur `--remote-auth-token-env`. Ein WebSocket-Handshake ohne Token bekommt 401. Eine zweite Bridge startet eine echte TUI über das gebündelte PTY mit `--remote` und `--remote-auth-token-env`; sie zeigt das Codex-Banner, und die Sitzungsidentität ist nicht `unavailable`. Das ist die Windows-Kette, ausgeführt auf macOS.

### Installer (19 Tests)

```sh
python3 -B -m unittest discover -s tests
```

Ergebnis: 19 Tests grün. 18 in `tests/test_setup.py`, 1 End-to-End-Test in `tests/test_e2e.py` (echtes Host-Bundle plus Rolle, Skill und MCP in einen künstlichen Vault mit angepasstem Basiscode, Rollback bytegleich).

Weiterhin geprüft: idempotentes Apply und Rollback, Preflight-Konflikt verhindert jedes Schreiben, Rollback verweigert spätere Member-Änderungen, manipuliertes Manifest oder Payload, Pfadgrenzen und Symlinks, keine Anmeldedateien, Claude-only ohne Codex, Linux darf inspizieren aber nicht installieren, private Stage-Ordner, unterbrochenes Apply mit Rollback, Companion-Änderungen blockieren ein Update, Companion-Installation lässt Basis und `data.json` unangetastet.

Neu in 0.2.0:

- Windows-Plan mit Host und AGENTS.md.
- Brain außerhalb des Vaults ergänzt `writable_roots` und den Projekt-Pointer.
- AGENTS.md erhält vorhandenen Member-Text und ist rückbaubar.
- `discover` listet Vaults aus `obsidian.json`.
- `inspect` listet MCP-Namen ohne Secrets.
- Umbenannter Config-Ordner wird erkannt.

### Planner (15 Tests)

```sh
python3 -B -m unittest integrations.test_planner
```

Ergebnis: 15 Tests grün. Unveränderte Fachprompts inklusive Zeilenumbrüchen, TOML-Erhalt, Konflikte, bestehende deaktivierte MCPs, Secret-Filter, Auswahl ohne implizite Deinstallation, ausführbare Skill-Dateien.

### Summe

44 Tests: 10 Host, 19 Installer, 15 Planner.

### Paketprüfung

`scripts/package.py` erzeugt das ZIP aus einer Dateiliste mit festem Zeitstempel 2026-09-20 und scannt Textdateien auf private Pfade (macOS-Benutzerordner und neu Windows-Profilpfade mit Laufwerk, Users und Benutzername) sowie typische Credential-Muster. Konfigurations-Snapshots und Testdaten sind nicht im Paket. Diese Musterprüfung ersetzt keine Prüfung später hinzugefügter Inhalte.

## Was offen ist

- **Echter Windows-Rechner.** Kein Lauf. Der WebSocket-Transport wurde auf macOS im Windows-Modus verifiziert, die ConPTY-Prebuilds (`win32-x64`, `win32-arm64`) sind die des öffentlichen Agentic-OS-Plugins v0.2.2 und wurden hier nicht ausgeführt. Offen sind damit: ConPTY-Start in Obsidian unter Windows, `codex.exe`-Suche auf einem echten System, `taskkill /t`, `icacls` auf Plan-Ordnern.
- **Intel-Mac.** Prebuild `darwin-x64` enthalten, nicht ausgeführt.
- **Linux.** Kein Prozessstart, bewusst.
- **Native Obsidian-Abnahme.** Nicht in einer separaten Obsidian-Instanz belegt. Die Abnahme erfolgt durch die Mitglieder über den Beweislauf in `SETUP-PROMPT.md`, Schritt 7: Codex nennt den Gedächtnis-Index und zitiert daraus, schreibt `memory/codex-testlauf.md` samt Indexzeile, die Claude anschließend liest, dann „Stoppen“ und „Sitzung fortsetzen“ mit demselben Verlauf. Erst ein gemeldeter Abschlussbericht aus Schritt 8 zählt als bestandene Abnahme.
- **Modellturn.** Kein Teil der automatisierten Tests. Der erste echte Turn ist Schritt 7 des Beweislaufs.
- **MCP-Anmeldung und Leseaufruf** mit dem Member-Konto. Konfiguriert heißt nicht getestet.
- **Nativer Profiltest** (`integrations/test_native_profile.py`) ist nicht Teil der 44 gezählten Tests.
- **Chat-Drawer-Umschaltung** im Hauptplugin: nicht enthalten.

Der Stand ist ein technisch geprüftes Paket für macOS mit einem vorbereiteten, auf macOS simulierten Windows-Pfad. Die Freigabe für Windows steht unter dem Vorbehalt des ersten echten Laufs.
