# Einrichtung für den betreuenden Coding-Agenten

Arbeite mit diesem konkreten Paket. Verwende keine privaten Pfade oder Zugangsdaten des Erstellers. Lies vor Änderungen den gesamten Ablauf.

## Bestehendes Setup erfassen

Ermittle den tatsächlichen lokalen Obsidian-Vault und das Benutzerverzeichnis. Wenn mehrere Vaults infrage kommen, frage nach dem gewünschten. Codex ist optional. Wer bei Claude bleiben möchte, braucht keine Änderungen.

Prüfe Python ab 3.11. Im Source-Checkout fehlt möglicherweise `host/build`. Baue dann isoliert mit `npm ci` und `npm run build` unter host/. Es gibt keinen Deploy-Hook. Das fertige Release-Paket enthält das Build bereits.

```sh
python3 scripts/setup.py inspect --vault /absoluter/pfad/zum/vault
```

Der Bericht enthält keine Agentenprompts oder MCP-Schlüssel. Er erkennt vorhandenen Basiscode, Quellzugriff, den Codex-Provider und lokale Rollen/Skills. Ein Fork wird nicht anhand seiner Versionsnummer für kompatibel erklärt. Der Zusatz installiert sich in einen separaten Plugin-Ordner und ersetzt den Basiscode nicht.

Verwendet das Mitglied einen abweichenden Obsidian-Konfigurationsordner statt `.obsidian` oder ein benutzerdefiniertes CODEX_HOME, stoppe die automatische Installation und kläre den Pfad. Diese erste Installer-Fassung unterstützt die Standardordner. Ein bestehender privater Agentic-OS-Codex-Provider braucht möglicherweise keinen weiteren Zusatz. Erkläre in diesem Fall den Unterschied, bevor ein zweites Terminal installiert wird.

## Auswahl und konkreter Plan

Wähle mit dem Mitglied nur tatsächlich benötigte vorhandene Rollen und Skills aus. Es wird kein persönlicher Agentenkatalog des Erstellers mitinstalliert. Notion/Linear können unabhängig von einer bestehenden Claude-MCP-Definition explizit ausgewählt werden. Andere MCP-Namen werden aus vorhandenen Definitionen geprüft. Nicht automatisch übernehmbare Verbindungen bleiben als konkrete manuelle Schritte sichtbar.

```sh
python3 scripts/setup.py plan --vault /absoluter/pfad/zum/vault --agent writer --skill research --mcp notion --output .local/setup-001
```

`writer` und `research` sind Beispiele und dürfen nur durch tatsächlich gefundene Namen ersetzt werden. Ohne diese Optionen werden keine Rollen, Skills oder MCPs übernommen. Für Claude-only kann `--mode claude-only` verwendet werden; der Plan enthält keine Zieländerungen.

Zeige die betroffenen Pfade, Statusmeldungen und Anmeldeschritte, nicht die vollständigen Payloads. `.local/setup-001` enthält lokale Snapshots und bleibt privat, außerhalb von Git und Uploads. Bei Konflikten nicht manuell weiterkopieren. Den Konflikt erklären und mit einer gezielten Anpassung einen neuen Plan erzeugen.

## Anwenden

Verwende den SHA256 aus der erfolgreichen Plan-Ausgabe. Wenn die Einrichtung bereits beauftragt ist und der Plan im gewählten Umfang bleibt, ist keine weitere Routinefreigabe erforderlich.

```sh
python3 scripts/setup.py apply --plan .local/setup-001 --sha256 HASH_AUS_DER_PLAN_AUSGABE
```

Alle Originalhashes werden vor dem ersten Schreiben erneut geprüft. Bereits angewandte Pläne sind wiederholbar, solange niemand die installierten Dateien verändert hat. Mitglieder-Einstellungen in `data.json`, der Basis-Plugin-Code und `community-plugins.json` werden nicht geändert. Das Plugin wird nicht automatisch aktiviert und bestehende Sessions werden nicht neu geladen.

Bei einem unterbrochenen Lauf bleibt ein Journal für Rollback bestehen. Ein nach einem Prozessabbruch übrig gebliebenes Lock darf erst nach Nachweis des beendeten Prozesses durch den betreuenden Agenten archiviert werden. Niemals zwei Installationen gleichzeitig auf denselben Vault anwenden.

## Anmelden und in Obsidian aktivieren

Wenn Codex fehlt, nutze die [offizielle CLI-Anleitung](https://developers.openai.com/codex/cli/). Installiere eine zum Host passende CLI. Die Implementierung wurde mit Codex CLI 0.153.4 entwickelt. Spätere oder ältere Versionen benötigen einen Laufzeittest, insbesondere für `app-server` und `--remote`.

```sh
codex login
codex mcp login notion
```

Den MCP-Login nur für eine tatsächlich ausgewählte OAuth-Verbindung starten. Das Mitglied autorisiert selbst das richtige Konto. Schlüssel für andere Dienste über deren native lokale Einrichtung verwalten, niemals im Chat einsammeln oder aus Claude-Dateien kopieren.

Danach in Obsidian die Community-Plugins neu erkennen lassen und „Agentic OS Codex“ einschalten. Ein erforderlicher Obsidian-Neustart geschieht erst, wenn laufende Sessions gesichert sind. Über den Befehl „Codex-Terminal öffnen“ erscheint die Zusatzansicht. Erst der bewusste Start darin startet Codex. Der bisherige Chat-Drawer bleibt unverändert.

## Prüfung und Wiederaufnahme

```sh
python3 scripts/setup.py doctor --vault /absoluter/pfad/zum/vault
```

Doctor prüft die Installation und gegebenenfalls den nativen Login-Status. Er führt keine Modell- oder MCP-Tool-Aufrufe aus. In der tatsächlichen Codex-Ansicht anschließend einen harmlosen Auftrag mit einer ausgewählten Rolle starten, einen ausgewählten Skill prüfen und pro MCP einen passenden Leseaufruf ausführen. Rolle, Tools, eigene Projekte und Resume getrennt prüfen. Ohne diese Nachweise bleibt die funktionale Abnahme offen.

Nach einem unterbrochenen OAuth-Ablauf den bestehenden Plan erneut anwenden beziehungsweise Doctor ausführen und beim offenen Login-Schritt weiterarbeiten. Nicht die gesamte Konfiguration neu erzeugen. Das Entfernen einer Auswahl deinstalliert nichts.

## Rollback und Updates

```sh
python3 scripts/setup.py rollback --plan .local/setup-001 --sha256 HASH_AUS_DER_PLAN_AUSGABE
```

Rollback stellt nur unverändert vorliegende Installationsänderungen zurück. Neue Dateien wandern ins lokale Rollback-Archiv. Hat das Mitglied inzwischen eine betroffene Datei bearbeitet, stoppt der Vorgang. Vor dem Entfernen eines aktivierten Plugin-Pakets dieses in Obsidian deaktivieren, ohne andere Sessions abzubrechen.

Updates bekommen immer einen neuen Plan. Die Eigentumsdateien des Installers erkennen eigene Paketdateien und verwaltete TOML-Blöcke. Lokale Änderungen werden nicht still überschrieben.
