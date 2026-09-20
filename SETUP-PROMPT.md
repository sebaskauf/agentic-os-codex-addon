# Setup-Prompt

Kopier den ganzen Block unter der Linie und füg ihn in Claude Code ein. Codex geht auch, dann arbeitet Codex die Schritte ab.

Rechne mit dreißig bis fünfundvierzig Minuten. Der größte Teil ist Warten auf Downloads und zwei Anmeldungen, die du selbst machst.

**Was du vorher wissen solltest**

1. **Du brauchst ein bestehendes Agentic OS** in einem Obsidian-Vault (System 2) und am besten dein Second Brain (System 1). Ohne Agentic OS bricht das Setup ab, das ist gewollt.
2. **Codex läuft mit deinem ChatGPT-Konto**, nicht mit Claude. Free und Go reichen zum Ausprobieren, für tägliche Arbeit ist Plus die sinnvolle Untergrenze. Das Setup kauft nichts und legt kein Konto an, du meldest dich selbst an.
3. **Codex bekommt Schreibzugriff auf deinen Vault**, genau wie Claude. Beide lesen und schreiben dasselbe Gedächtnis. Wenn du das nicht willst, sag es im ersten Schritt, dann bleibt Codex ohne gemeinsames Gedächtnis.
4. **Mac und Windows.** Auf dem Mac läuft die Verbindung über einen privaten Socket, unter Windows über einen lokalen Port mit Zufallstoken. Die Windows-Technik ist dieselbe, die das Agentic OS selbst unter Windows nutzt. Wer als Erster auf Windows durchläuft, schickt mir bitte den Abschlussbericht aus Schritt 8.

---

Richte mir die Codex-Erweiterung für mein Agentic OS aus diesem Repo ein und verbinde Codex mit demselben Gedächtnis, das Claude benutzt: https://github.com/sebaskauf/agentic-os-codex-addon

Arbeite die Schritte der Reihe nach ab. Schlägt etwas fehl, zeig mir die genaue Fehlermeldung und was du brauchst, statt den Schritt als erledigt zu melden oder ihn zu überspringen. Entscheide nichts für mich, was mich Geld, Daten oder ein Konto kostet. Kopiere nie Zugangsdaten, Tokens oder Passwörter, weder aus Dateien noch aus dem Chat, und zeig mir nie den Inhalt meiner Konfigurationsdateien im Klartext.

SCHRITT 0 - WO BIN ICH, WAS HABE ICH
1. Sag mir zuerst, in welchem Ordner du gerade bist, und leg auf mein Ja einen Arbeitsordner an. Vorschlag: `~/Documents/Codex-Addon` auf dem Mac, `%USERPROFILE%\Documents\Codex-Addon` unter Windows. Dort landen Download, Pläne und das Protokoll. Dieser Ordner ist ab jetzt "mein Arbeitsordner".
2. Merk dir mein Betriebssystem, meine Architektur und meine Shell. Unter Windows arbeitest du in PowerShell: keine `&&`-Ketten (Windows PowerShell 5.1 kennt sie nicht), jeder Befehl einzeln, `~` heißt dort `$env:USERPROFILE`. Verwende überall den Python-Aufruf, der bei mir funktioniert: `python3` auf dem Mac, `python` oder `py -3` unter Windows. Ich schreibe unten `python3`, du ersetzt es.
3. Prüf still: `python3 --version` gibt mindestens 3.11 (der Installer braucht das), `git --version`, und ob du Websuche nutzen kannst. Fehlt Python: Mac `brew install python` oder python.org, Windows `winget install -e --id Python.Python.3.12` und danach ein neues Terminal. Das ist eine Installation, frag mich vorher.

SCHRITT 1 - DAS PAKET HOLEN
1. Lade das fertige Release in meinen Arbeitsordner. Es enthält die gebaute Erweiterung für Mac (Apple Silicon und Intel) und Windows (x64 und ARM), Node.js ist nicht nötig.
   Mac: `curl -L -o addon.zip https://github.com/sebaskauf/agentic-os-codex-addon/releases/latest/download/agentic-os-codex-addon.zip` und dann `unzip -o addon.zip`
   Windows: `Invoke-WebRequest -Uri https://github.com/sebaskauf/agentic-os-codex-addon/releases/latest/download/agentic-os-codex-addon.zip -OutFile addon.zip` und dann `Expand-Archive -Force addon.zip .`
2. Der entpackte Ordner heißt `agentic-os-codex-addon`. Lies dort `README.md` und `INSTALL.md`. Sag mir die Version aus `host/build/manifest.json` und ob in `host/build/native/` ein Ordner für meine Plattform liegt (`darwin-arm64`, `darwin-x64`, `win32-x64` oder `win32-arm64`). Fehlt er oder ist das Archiv leer, brich ab und sag es mir.
3. Alle weiteren Befehle laufen aus diesem entpackten Ordner.

SCHRITT 2 - BESTANDSAUFNAHME
Bevor irgendwas geändert wird, will ich wissen, wo ich stehe. Lauf `python3 scripts/setup.py discover`. Das ist nur Lesen. Ergänze, was das Skript nicht sieht, und zeig mir am Ende EINE Tabelle mit drei Spalten: was, Stand (da / fehlt / nicht nötig), was das für mich bedeutet. Frag mich nichts, was du selbst nachsehen kannst.
1. Betriebssystem, Architektur, Python-Version, und ob `supported_host_install` wahr ist.
2. Meine Obsidian-Vaults aus der Ausgabe. Welcher hat `agentic_os: true`? Genau einer: nimm ihn. Mehrere: frag mich, welchen. Keiner: dann steht mein Agentic OS noch nicht, stopp hier und sag mir, dass System 2 zuerst kommt. Der gewählte Vault ist ab jetzt "mein Vault".
3. Mein Second Brain. Liegen in meinem Vault `CLAUDE.md` und `memory/MEMORY.md` (`claude_md`, `memory_index`)? Wenn ja, ist mein Vault mein Gehirn, fertig. Wenn nein, frag mich EINMAL: liegt mein Second Brain in einem anderen Ordner (dann brauchst du den Pfad), oder habe ich noch keins (dann kommt System 1 zuerst; wir können trotzdem weitermachen, Codex legt den Index dann beim ersten Eintrag an).
4. Claude Code: `claude --version`. Und wo Claude sein Gedächtnis ablegt: gibt es in `~/.claude/settings.json` oder `<vault>/.claude/settings.json` ein `autoMemoryDirectory`? Notier den Pfad, ohne den Rest der Datei zu zeigen.
5. Codex: `codex --version`. Fehlt Codex, wird das Schritt 3. Ist es da: `codex login status`, und sag mir ehrlich, ob ich angemeldet bin.
6. Mein ChatGPT-Plan: frag mich EINMAL (Free, Go, Plus, Pro, Business). Codex läuft mit allen, der Unterschied ist die Zahl der Nachrichten pro fünf Stunden. Das ist eine Information, keine Kaufempfehlung.
7. Meine Claude-Agents, Skills und MCPs: `python3 scripts/setup.py inspect --vault <mein Vault>` listet die Namen unter `agents`, `skills` und `mcps`. Zeig sie mir als Liste. Der Bericht enthält keine Prompts und keine Schlüssel.
8. Läuft Obsidian gerade? Mac `pgrep -x Obsidian`, Windows `Get-Process Obsidian -ErrorAction SilentlyContinue`. Merk dir das für Schritt 6.

Sag mir nach der Tabelle in zwei Sätzen, was das Setup bei mir konkret tun wird und was nicht. Danach fragst du, ob wir so weitermachen.

**Sichere laufend:** Schreib nach jedem Schritt, was du weißt, als `CODEX-SETUP.md` in meinen Arbeitsordner, mit `setup: unvollständig` im Kopf. Werde ich unterbrochen, machst du beim nächsten Mal dort weiter, statt von vorn zu fragen. Liegt die Datei schon da und steht dort `setup: fertig`, frag mich, ob ich wirklich neu einrichten will.

SCHRITT 3 - CODEX INSTALLIEREN UND ANMELDEN
Nur, was fehlt. Frag mich vor jeder Installation.
1. Fehlt Codex:
   - Mac: `npm install -g @openai/codex` (wenn npm da ist). Ohne npm: `brew install codex`. Ist die ChatGPT-Desktop-App installiert und existiert `/Applications/ChatGPT.app/Contents/Resources/codex`, reicht ein Link: `mkdir -p ~/.local/bin` und `ln -s /Applications/ChatGPT.app/Contents/Resources/codex ~/.local/bin/codex`.
   - Windows: der offizielle Installer `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"`, alternativ `npm install -g @openai/codex`. Danach ein neues Terminal öffnen. Die npm-Variante legt `codex.cmd` an, die Erweiterung findet daneben von selbst die echte `codex.exe`.
   - Klappt beides nicht, recherchier die offizielle Anleitung unter https://developers.openai.com/codex/cli und zeig mir den Weg, statt zu raten.
   Danach `codex --version`. Ich will mindestens 0.155.
2. Anmelden: `codex login`. Das öffnet den Browser, ich melde mich selbst mit meinem ChatGPT-Konto an, du wartest. Danach `codex login status`. Erst wenn das "logged in" zeigt, gilt es als angemeldet.
3. Nur Windows: Codex bringt eine eigene Sandbox mit, in der es Befehle ausführt. Beim ersten Start fragt es eventuell nach deren Einrichtung (`/setup-default-sandbox`). Erklär mir in zwei Sätzen, dass das die Schutzschicht ist, und lass mich das selbst bestätigen.

SCHRITT 4 - DER PLAN
Der Installer ändert nichts, bevor ich den Plan gesehen habe.
1. Frag mich, welche meiner Claude-Agents aus Schritt 2.7 Codex auch bekommen soll. Nur die, die ich nenne; ohne Angabe wird keiner übernommen. Jeder übernommene Agent wird ein Codex-Profil mit dem unveränderten Prompt. Dasselbe für Skills. Bei MCPs: Notion und Linear gehen als fertige Rezepte (`--mcp notion`), andere nur, wenn sie eine einfache https-Adresse ohne Schlüssel haben. Alles andere meldet der Plan als `manual-setup`, und du erklärst mir danach, wie ich es in Codex selbst einrichte. Schlüssel werden nie kopiert.
2. Lauf: `python3 scripts/setup.py plan --vault <mein Vault> --output <mein Arbeitsordner>/plan-001` plus `--agent NAME`, `--skill NAME`, `--mcp NAME` je Auswahl. Liegt mein Second Brain nicht im Vault: zusätzlich `--brain <Pfad>`. Will ich ausdrücklich kein gemeinsames Gedächtnis: `--no-brain`.
3. Zeig mir aus der Ausgabe: die betroffenen Dateipfade (nur Pfade), die `statuses`, die `manual_steps` und den `sha256`. Erklär mir in je einem Satz, was die drei Dinge tun: `AGENTS.md` im Vault (sagt Codex, wo mein Gedächtnis liegt und wie es dort schreibt), der `[projects]`-Block in der Codex-Konfiguration (mein Vault gilt als vertrauenswürdig, sonst fragt Codex bei jedem Schreiben), und die Profile (meine übernommenen Agents).
4. Der Plan-Ordner enthält Schnappschüsse meiner Codex-Konfiguration. Er bleibt in meinem Arbeitsordner, wird nicht in Git eingecheckt und nirgends hochgeladen.

SCHRITT 5 - ANWENDEN UND PRÜFEN
1. `python3 scripts/setup.py apply --plan <mein Arbeitsordner>/plan-001 --sha256 <der Hash aus Schritt 4>`. Genau dieser Hash, kein anderer.
2. Kommt ein Fehler mit "changed since inspection", "member changes" oder "review required": nichts von Hand weiterkopieren. Erklär mir den Konflikt, dann machst du einen neuen Plan mit anderem Ordnernamen (`plan-002`).
3. `python3 scripts/setup.py doctor --vault <mein Vault>` und zeig mir `brain_link`, `codex_login`, `companion_enabled` und `host_native_available`. `brain_link` muss `configured` sein, wenn ich das gemeinsame Gedächtnis wollte.
4. Lies mir den Block vor, der jetzt oben in `<mein Vault>/AGENTS.md` steht. Eigener Text, der dort vorher stand, muss unverändert darunter liegen.

SCHRITT 6 - IN OBSIDIAN EINSCHALTEN
1. Sag mir, dass Obsidian jetzt einmal neu laden muss und dass dabei offene Terminals im Agentic OS schließen. Ich sag dir, wann es passt. Neu laden: Befehlspalette (Cmd+P auf dem Mac, Ctrl+P unter Windows), "Reload app without saving".
2. Dann: Einstellungen, Community-Plugins, "Agentic OS Codex" einschalten. Befehlspalette: "Codex-Terminal öffnen". Beschreib mir, was ich sehe: eine Leiste mit dem Claude-Button, der Profil-Auswahl ("Codex Standard" plus meine übernommenen Agents), dem Arbeitsordner (vorbelegt mit meinem Vault) und "Codex starten".
3. Ich klicke "Codex starten". Sag mir vorher, was erscheinen soll: das Codex-Banner mit Versionsnummer, danach der Prompt. Erscheint stattdessen eine Meldung, gib sie mir wörtlich weiter und such die Ursache: "Terminalpaket fehlt" heißt falsche Plattform im Paket, "Codex-App-Server startet nicht" heißt meist Codex nicht angemeldet oder eine zu alte Version.

SCHRITT 7 - DER BEWEIS
Ein Setup, das nie gelaufen ist, ist kein Setup. Drei Prüfungen, jede mit Ergebnis, das du mir nennst.
1. Lesen. Ich tippe im Codex-Fenster: "Welche Datei ist mein Gedächtnis-Index, und was steht in den ersten drei Zeilen?" Codex muss `memory/MEMORY.md` (oder den Index aus meinem Second-Brain-Ordner) nennen und daraus zitieren. Nennt es etwas anderes oder weiß es nichts davon, ist `AGENTS.md` nicht geladen: prüf dann, ob Codex wirklich in meinem Vault gestartet wurde (Arbeitsordner in der Leiste) und ob `AGENTS.md` dort liegt.
2. Schreiben. Ich tippe im Codex-Fenster: "Leg im Gedächtnis einen Eintrag `codex-testlauf` an, dass Codex seit heute mit im Agentic OS läuft, im selben Format wie die vorhandenen Einträge, und trag ihn im Index ein." Danach prüfst DU mit Read: liegt `memory/codex-testlauf.md` mit Frontmatter da, steht die Zeile im Index? Sag mir, was du gefunden hast. Beides da: das gemeinsame Gedächtnis funktioniert in beide Richtungen, weil du (Claude) gerade gelesen hast, was Codex geschrieben hat.
3. Fortsetzen. Ich klicke "Stoppen" und danach "Sitzung fortsetzen". Codex muss dieselbe Unterhaltung wieder öffnen, mit dem Testeintrag im Verlauf. Kommt "Keine gesicherte Codex-Session-ID", war die Sitzung noch zu jung, dann einmal wiederholen.
4. Nur wenn ich MCPs übernommen habe: `codex mcp login <name>` im Codex-Fenster, ich melde mich selbst an, danach ein harmloser Leseaufruf (zum Beispiel eine Seite suchen). Konfiguriert heißt nicht getestet.
Scheitert eine Prüfung: zeig mir die genaue Meldung und was ich tun kann. Setz `CODEX-SETUP.md` dann auf `setup: fertig` mit dem Vermerk, welche Prüfung offen ist. Blockier mich nicht mit einem Setup, das nie fertig wird.

SCHRITT 8 - ABSCHLUSS
1. Zeig mir eine kurze Übersicht: Plattform und Architektur, Codex-Version, mein Vault, mein Gedächtnis-Index, übernommene Agents, Skills und MCPs mit Stand je Eintrag, die drei Prüfungen aus Schritt 7 mit Ergebnis, und was offen ist.
2. Schreib genau diese Übersicht in `CODEX-SETUP.md` und setz `setup: fertig`.
3. Sag mir, wie ich es ab jetzt benutze: Codex-Tab im Agentic OS öffnen, Profil wählen, starten. Beide Agenten lesen und schreiben dasselbe Gedächtnis, die Regeln aus `CLAUDE.md` gelten für beide. Den verwalteten Block in `AGENTS.md` nicht von Hand ändern, eigener Text davor oder dahinter ist erlaubt. Neue Agents später: derselbe Prompt noch einmal, nur Schritt 4 mit `--agent`.
4. Rückbau, falls ich es wieder loswerden will: `python3 scripts/setup.py rollback --plan <mein Arbeitsordner>/plan-001 --sha256 <Hash>`. Das stellt nur her, was seitdem niemand verändert hat.
5. Lösch `addon.zip` aus meinem Arbeitsordner, den entpackten Ordner und den Plan-Ordner lässt du liegen.
