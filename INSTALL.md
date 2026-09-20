# Einrichtung für den betreuenden Coding-Agenten

Arbeite mit diesem konkreten Paket. Verwende keine privaten Pfade oder Zugangsdaten des Erstellers. Der Ablauf für Mitglieder steht in `SETUP-PROMPT.md`; diese Datei erklärt die Werkzeuge dahinter.

Alle Befehle laufen aus dem Paketordner. `python3` steht für den Python-Aufruf des Rechners (`python` oder `py -3` unter Windows). Unter Windows arbeitest du in PowerShell, ein Befehl je Zeile.

## Bestandsaufnahme

```sh
python3 scripts/setup.py discover
python3 scripts/setup.py inspect --vault /absoluter/pfad/zum/vault
```

`discover` liest Obsidians Vault-Liste (`obsidian.json` je Plattform) und zeigt pro Vault, ob dort ein Agentic OS, ein Companion, eine `CLAUDE.md` und ein Gedächtnis-Index (`memory/MEMORY.md`) liegen, dazu die gefundenen Werkzeuge und die Codex-Version. Bei mehreren Vaults mit Agentic OS fragst du das Mitglied.

`inspect` erfasst den gewählten Vault: Agentic-OS-Version und Fork-Hash, Config-Ordner (auch ein umbenannter `.obsidian`-Ordner wird erkannt), Companion-Stand, den Gedächtnisstand (`brain`), die Namen der lokalen Rollen, Skills und MCPs, und ob die Terminaldateien für diese Plattform im Paket liegen (`host_native_available`). Der Bericht enthält keine Prompts und keine Schlüssel.

Ein benutzerdefiniertes `CODEX_HOME` stoppt die automatische Installation. Kläre dann den Pfad, statt zu raten.

## Plan

```sh
python3 scripts/setup.py plan --vault /absoluter/pfad/zum/vault --agent writer --skill research --mcp notion --output /pfad/arbeitsordner/plan-001
```

- Ohne `--agent`, `--skill`, `--mcp` werden keine Rollen, Skills oder MCPs übernommen. Nur tatsächlich gefundene Namen verwenden.
- Das gemeinsame Gedächtnis ist Standard: der Plan enthält einen verwalteten Block am Anfang von `<vault>/AGENTS.md` und den Block `[projects."<vault>"] trust_level = "trusted"` in `~/.codex/config.toml`. Liegt das Second Brain in einem anderen Ordner: `--brain /pfad/zum/brain` ergänzt diesen Ordner als vertrauenswürdiges Projekt und als zusätzlichen Schreibpfad (`sandbox_workspace_write.writable_roots`). `--no-brain` lässt das Gedächtnis komplett aus.
- `--mode claude-only` erzeugt einen leeren Plan.

Zeig dem Mitglied die betroffenen Pfade, `statuses`, `manual_steps` und den `sha256`, nicht die Payloads. Der Plan-Ordner enthält Schnappschüsse der Codex-Konfiguration und bleibt privat: nicht in Git, nicht hochladen. Unter Windows wird er per ACL auf den Benutzer beschränkt.

## Anwenden

```sh
python3 scripts/setup.py apply --plan /pfad/arbeitsordner/plan-001 --sha256 HASH_AUS_DER_PLAN_AUSGABE
```

Alle Originalhashes werden vor dem ersten Schreiben erneut geprüft. Angewandte Pläne sind wiederholbar, solange niemand die installierten Dateien verändert hat. `data.json` des Mitglieds, der Basis-Plugin-Code und `community-plugins.json` werden nicht geändert. Das Plugin wird nicht automatisch aktiviert. Eigener Text in `AGENTS.md` bleibt unter dem verwalteten Block erhalten.

Bei Konflikten ("changed since inspection", "member changes", "review required") nicht von Hand weiterkopieren: Konflikt erklären, neuen Plan mit neuem Ordnernamen erzeugen. Ein nach einem Prozessabbruch übrig gebliebenes Lock erst nach Nachweis des beendeten Prozesses archivieren. Nie zwei Installationen gleichzeitig auf denselben Vault.

## Codex installieren und anmelden

Fehlt Codex, folge der offiziellen Anleitung unter https://developers.openai.com/codex/cli. Mac: `npm install -g @openai/codex` oder `brew install codex`; liegt die ChatGPT-Desktop-App vor, reicht ein Link auf deren mitgelieferte Binary (`/Applications/ChatGPT.app/Contents/Resources/codex`). Windows: `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"` oder `npm install -g @openai/codex`; die Erweiterung findet neben dem npm-Shim `codex.cmd` von selbst die echte `codex.exe`. Entwickelt gegen Codex CLI 0.155; ältere Versionen brauchen einen Laufzeittest für `app-server` und `--remote`.

```sh
codex login
codex login status
codex mcp login notion
```

Das Mitglied meldet sich selbst an. MCP-Logins nur für tatsächlich ausgewählte OAuth-Verbindungen. Schlüssel anderer Dienste über deren native Einrichtung verwalten, nie im Chat einsammeln oder aus Claude-Dateien kopieren.

## In Obsidian aktivieren

Obsidian neu laden (offene Cockpit-Terminals schließen dabei, Zeitpunkt vom Mitglied bestätigen lassen), dann Community-Plugins, "Agentic OS Codex" einschalten, Befehl "Codex-Terminal öffnen". Erst der Klick auf "Codex starten" startet einen Prozess. Der bisherige Chat-Drawer bleibt unverändert.

## Prüfung, Beweislauf, Wiederaufnahme

```sh
python3 scripts/setup.py doctor --vault /absoluter/pfad/zum/vault
```

Doctor prüft Installation, `brain_link` (verwalteter Block in `AGENTS.md` vorhanden), `companion_enabled`, `host_native_available` und den Login-Status. Er führt keine Modell- oder MCP-Aufrufe aus.

Der Beweis läuft in der echten Codex-Ansicht (Schritt 7 im Setup-Prompt): Codex nennt den Gedächtnis-Index und zitiert daraus, Codex schreibt einen Testeintrag samt Indexzeile, den Claude danach liest, und "Sitzung fortsetzen" öffnet dieselbe Unterhaltung. Pro übernommenem MCP zusätzlich ein Leseaufruf. Ohne diese Nachweise bleibt die funktionale Abnahme offen.

Nach einem unterbrochenen Ablauf den bestehenden Plan erneut anwenden beziehungsweise Doctor ausführen und beim offenen Schritt weiterarbeiten. Nicht die gesamte Konfiguration neu erzeugen.

## Rollback und Updates

```sh
python3 scripts/setup.py rollback --plan /pfad/arbeitsordner/plan-001 --sha256 HASH_AUS_DER_PLAN_AUSGABE
```

Rollback stellt nur unverändert vorliegende Installationsänderungen zurück, auch den Block in `AGENTS.md`. Neue Dateien wandern ins lokale Rollback-Archiv. Hat das Mitglied eine betroffene Datei inzwischen bearbeitet, stoppt der Vorgang. Vor dem Entfernen eines aktivierten Plugin-Pakets dieses in Obsidian deaktivieren.

Updates bekommen immer einen neuen Plan. Die Eigentumsdateien des Installers erkennen eigene Paketdateien, verwaltete TOML-Blöcke und den `AGENTS.md`-Block. Lokale Änderungen werden nicht still überschrieben.

## Aus dem Quellcode

Der Source-Checkout enthält kein `host/build`. Baue es mit Node.js: `cd host`, `npm ci --ignore-scripts --no-audit --no-fund`, `npm run build`. Das Release-Paket enthält das Build bereits.
