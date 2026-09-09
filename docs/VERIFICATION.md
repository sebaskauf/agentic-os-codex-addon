# Abnahmestand der Pilotfassung

Stand 09.09.2026. Getestet auf macOS Apple Silicon mit Codex CLI 0.153.4. Keine Installation in einem produktiven Vault und keine Modellanfrage für diese Abnahme.

## Bestandene Prüfungen

13 Installer-Tests prüfen Staging, Manifest- und Payload-Manipulation, Pfadgrenzen, Symlinks, Anmeldedateien, Abbruchjournal, Drift vor Installation, spätere Member-Änderungen, idempotentes Apply und selektiven Rollback. Ein vollständiger Test installiert das echte Host-Bundle samt Rolle, Skill und Notion-Konfiguration in einen künstlichen Member-Vault. Der vorhandene angepasste Basiscode und die eigenen Einstellungen bleiben bytegleich. Ein zweiter Plan hat null Änderungen. Rollback stellt die ursprüngliche Codex-Konfiguration wieder her.

15 Integrations-Tests prüfen unveränderte Fachprompts einschließlich Zeilenumbrüchen, TOML-Erhalt, Konflikte, bestehende deaktivierte MCPs, Secret-Filter, Auswahl ohne implizite Deinstallation und ausführbare Skill-Dateien.

Ein zusätzlicher nativer Profiltest bestätigt, dass Codex CLI 0.153.4 die erzeugte NAME.config.toml über `-p NAME` tatsächlich lädt. Absichtlich nicht existierende Modellanbieter sorgen für einen lokalen Fehler, bevor ein Modellaufruf möglich ist.

Acht Host-Tests prüfen Zustand ohne automatischen Start, Argumente ohne zusätzliche Rechte, Thread-Zuordnung, ungültige Resume-Ziele, einen echten ARM64-Terminalprozess mit harmlosem Kommando und einen echten Codex-App-Server mit privaten Sockets ohne Modellturn. TypeScript und der isolierte Build bestehen.

Der Codex-Plugin-Validator und Skill-Validator bestehen. Das Paket wird aus einer Dateiliste erzeugt und auf konkrete private Benutzerpfade und typische Credential-Muster geprüft. Konfigurations-Snapshots und Testdaten sind nicht Teil des Release-Pakets. Diese Musterprüfung ersetzt keine Prüfung eigener später hinzugefügter Inhalte.

## Visuelle Prüfung

Die Browser-Vorschau lädt das tatsächliche Plugin-Bundle mit nachgebildeten Obsidian-Schnittstellen. Oberfläche und Profilauswahl wurden visuell geprüft. Der Screenshot liegt im Source-Repo unter host/test/ui-preview.png.

Der Versuch, Obsidian mit getrenntem User-Data-Verzeichnis und eigenem Test-Vault zu starten, endete unmittelbar. Die Computersteuerung fand anschließend nur die produktive Obsidian-Instanz. Dort wurden keine Aktionen durchgeführt. Die native Obsidian-Abnahme wurde daher nicht als bestanden gewertet.

## Vor Community-Freigabe offen

Ein echter Obsidian-Installationslauf auf einem separaten Test- oder Member-Rechner, ein tatsächlicher Modellturn mit ausgewählter Rolle, MCP-Anmeldung und Leseaufruf mit dem Member-Konto sowie Resume nach Obsidian-Neustart stehen aus. Intel-Prebuilds werden mitgeliefert, ihre Ausführung wurde nicht geprüft. Windows und Linux sind für diesen Pilot gesperrt.

Die vorhandene ChatDrawer-Umschaltung, Cutting-Cockpit-Integration und automatische Memory-Nachverarbeitung aus Sebastians persönlichem Ausbau sind nicht Bestandteil dieser Companion-Fassung. Ein Mitglied erhält die zusätzliche Codex-Ansicht und die ausdrücklich ausgewählten Integrationen.

Der Stand ist ein technisch geprüftes Pilotpaket mit klaren Laufzeitgrenzen, keine vollständig abgenommene öffentliche Community-Veröffentlichung.
