import { FileSystemAdapter, ItemView, Notice, Plugin, WorkspaceLeaf } from "obsidian";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import type { IPty } from "node-pty";
import { randomUUID } from "crypto";
import { existsSync, chmodSync, statSync } from "fs";
import { join, isAbsolute } from "path";
import { startCodexBridge, type CodexBridge } from "./codexBridge";
import { codexCommand, listCodexProfiles } from "./providers/codex";
import { readSettings, resumableThread, type HostSettings, type SavedSession } from "./state";

const VIEW = "agentic-os-codex-terminal";
const CLAUDE_COMMAND = "agentic-os:open-terminal-pane";
interface CommandHost { commands: { commands: Record<string, unknown>; executeCommandById(id: string): boolean }; }
const commands = (plugin: CodexAddon): CommandHost["commands"] | undefined => (plugin.app as unknown as Partial<CommandHost>).commands;

export default class CodexAddon extends Plugin {
  settings: HostSettings = { enabled: false, sessions: [] };
  private writes = Promise.resolve();
  private views = new Set<CodexView>();
  private active = new Map<string, CodexView>();
  claim(id: string, owner: CodexView): boolean { if (this.active.has(id)) return false; this.active.set(id, owner); return true; }
  release(id: string, owner: CodexView): void { if (this.active.get(id) === owner) this.active.delete(id); }
  async onload(): Promise<void> {
    this.settings = readSettings(await this.loadData());
    this.registerView(VIEW, leaf => {
      const view = new CodexView(leaf, this);
      this.views.add(view);
      return view;
    });
    this.addCommand({ id: "open-terminal", name: "Codex-Terminal öffnen", callback: () => void this.open() });
    this.addRibbonIcon("square-terminal", "Codex-Terminal öffnen", () => void this.open());
  }
  onunload(): void { for (const view of this.views) view.stop(); }
  remove(view: CodexView): void { this.views.delete(view); }
  basePath(): string {
    const adapter = this.app.vault.adapter;
    if (!(adapter instanceof FileSystemAdapter)) throw new Error("Dieses Plugin benötigt einen lokalen Desktop-Vault.");
    return adapter.getBasePath();
  }
  pluginPath(): string { return join(this.basePath(), this.app.vault.configDir, "plugins", this.manifest.id); }
  saveSession(session: SavedSession): void {
    const index = this.settings.sessions.findIndex(item => item.id === session.id);
    if (index < 0) this.settings.sessions.push({ ...session });
    else this.settings.sessions[index] = { ...session };
    this.settings.enabled = true;
    // Serialize writes so older metadata cannot overwrite a newer verified thread identity.
    const snapshot = JSON.parse(JSON.stringify(this.settings)) as HostSettings;
    this.writes = this.writes.then(() => this.saveData(snapshot)).catch(() => { new Notice("Codex-Sitzungsstand konnte nicht gespeichert werden."); });
  }
  async open(): Promise<void> {
    const leaf = this.app.workspace.getLeaf("tab");
    await leaf.setViewState({ type: VIEW, active: true, state: { id: randomUUID() } });
    await this.app.workspace.revealLeaf(leaf);
  }
}

export class CodexView extends ItemView {
  private session: SavedSession;
  private term?: Terminal;
  private fit?: FitAddon;
  private pty?: IPty;
  private bridge?: CodexBridge;
  private observer?: ResizeObserver;
  private status?: HTMLElement;
  private profile?: HTMLSelectElement;
  private cwd?: HTMLInputElement;
  private startButton?: HTMLButtonElement;
  private starting = false;
  private generation = 0;
  constructor(leaf: WorkspaceLeaf, private plugin: CodexAddon) {
    super(leaf);
    this.session = { id: randomUUID(), cwd: plugin.basePath() };
  }
  getViewType(): string { return VIEW; }
  getDisplayText(): string { return this.session?.profile ? `Codex · ${this.session.profile}` : "Codex"; }
  getIcon(): string { return "square-terminal"; }
  getState(): Record<string, unknown> { return { id: this.session.id }; }
  async setState(value: unknown, result: { history: boolean }): Promise<void> {
    if (!this.pty && !this.starting && value && typeof value === "object" && "id" in value && typeof value.id === "string") {
      this.session = { ...(this.plugin.settings.sessions.find(item => item.id === value.id) ?? { id: value.id, cwd: this.plugin.basePath() }) };
      if (!this.pty && !this.starting) this.render();
    }
    await super.setState(value, result);
  }
  async onOpen(): Promise<void> { this.render(); }
  async onClose(): Promise<void> {
    this.stop();
    this.observer?.disconnect();
    this.term?.dispose();
    this.plugin.remove(this);
  }
  private render(): void {
    this.observer?.disconnect();
    this.term?.dispose();
    this.contentEl.empty();
    this.contentEl.addClass("aos-codex-view");
    const toolbar = this.contentEl.createDiv({ cls: "aos-codex-toolbar" });
    const claude = toolbar.createEl("button", { text: "Claude in Agentic OS" });
    const host = commands(this.plugin);
    claude.disabled = !host?.commands[CLAUDE_COMMAND];
    claude.onclick = () => {
      if (!commands(this.plugin)?.executeCommandById(CLAUDE_COMMAND)) new Notice("Die Claude-Terminalfunktion dieser Agentic-OS-Version wurde nicht gefunden.");
    };
    this.profile = toolbar.createEl("select", { attr: { "aria-label": "Codex-Rollenprofil" } });
    this.profile.createEl("option", { text: "Codex Standard", value: "" });
    for (const name of listCodexProfiles()) this.profile.createEl("option", { text: name, value: name });
    if (this.session.profile && !listCodexProfiles().includes(this.session.profile)) this.profile.createEl("option", { text: `${this.session.profile} · fehlt`, value: this.session.profile });
    this.profile.value = this.session.profile ?? "";
    this.cwd = toolbar.createEl("input", { type: "text", attr: { "aria-label": "Arbeitsordner", title: "Arbeitsordner", name: "codex-workspace", autocomplete: "off", spellcheck: "false" } });
    this.cwd.value = this.session.cwd;
    this.startButton = toolbar.createEl("button", { text: this.session.threadId ? "Sitzung fortsetzen" : "Codex starten" });
    this.startButton.onclick = () => void this.start();
    const stop = toolbar.createEl("button", { text: "Stoppen" });
    stop.onclick = () => this.stop();
    const fresh = toolbar.createEl("button", { text: "Neue Sitzung" });
    fresh.onclick = () => void this.plugin.open();
    this.status = this.contentEl.createDiv({ cls: "aos-codex-status" });
    this.status.setAttribute("role", "status");
    this.status.setAttribute("aria-live", "polite");
    this.status.textContent = process.platform !== "darwin"
      ? "Diese Pilotversion unterstützt macOS. Unter Windows und Linux startet sie keinen Prozess."
      : host?.commands[CLAUDE_COMMAND]
        ? "Bereit. Startet erst nach deinem Klick. Profile und Berechtigungen stammen aus deiner Codex-Konfiguration."
        : "Agentic-OS-Terminalbefehl nicht gefunden. Codex kann separat genutzt werden. Dein bestehendes OS wird nicht verändert.";
    if (process.platform !== "darwin") this.startButton.disabled = true;
    const terminalEl = this.contentEl.createDiv({ cls: "aos-codex-terminal" });
    this.term = new Terminal({ cursorBlink: true, fontSize: 13, scrollback: 5000, theme: { background: "#171717", foreground: "#e8e8e8" }, allowProposedApi: false });
    this.fit = new FitAddon();
    this.term.loadAddon(this.fit);
    this.term.open(terminalEl);
    this.term.onData(data => this.pty?.write(data));
    this.observer = new ResizeObserver(() => {
      try { this.fit?.fit(); if (this.term) this.pty?.resize(this.term.cols, this.term.rows); } catch { /* Hidden pane has no dimensions yet. */ }
    });
    this.observer.observe(terminalEl);
  }
  private async start(): Promise<void> {
    if (this.pty || this.starting || process.platform !== "darwin") return;
    const cwd = this.cwd?.value.trim() ?? "";
    if (!isAbsolute(cwd) || !existsSync(cwd) || !statSync(cwd).isDirectory()) { new Notice("Bitte einen vorhandenen absoluten Arbeitsordner wählen."); return; }
    const selectedProfile = this.profile?.value || undefined;
    if (this.session.threadId && (cwd !== this.session.cwd || selectedProfile !== this.session.profile)) {
      new Notice("Für einen anderen Ordner oder ein anderes Profil bitte eine neue Sitzung öffnen."); return;
    }
    if (!this.plugin.claim(this.session.id, this)) { new Notice("Diese Sitzung ist bereits in einem anderen Codex-Fenster aktiv."); return; }
    this.session = { ...this.session, cwd, profile: selectedProfile };
    this.starting = true;
    const attempt = ++this.generation;
    if (this.startButton) { this.startButton.disabled = true; this.startButton.textContent = "Codex startet…"; }
    try {
      const bridge = await startCodexBridge({ tabId: this.session.id, launchId: randomUUID(), cwd, profile: selectedProfile, onMetadata: metadata => {
        if (attempt !== this.generation) return;
        if (metadata.identityStatus === "verified" && metadata.nativeThreadId) {
          this.session.threadId = resumableThread(metadata);
          this.plugin.saveSession(this.session);
        } else if (metadata.identityStatus === "unavailable") {
          this.session.threadId = undefined;
          this.plugin.saveSession(this.session);
        }
        if (this.status) this.status.textContent = `${metadata.status} · ${metadata.identityStatus}${metadata.model ? ` · ${metadata.model}` : ""}`;
      } });
      if (attempt !== this.generation) { bridge.dispose(); return; }
      this.bridge = bridge;
      const entry = join(this.plugin.pluginPath(), "native", `${process.platform}-${process.arch}`, "lib", "index.js");
      if (!existsSync(entry)) throw new Error(`Terminalpaket fehlt für ${process.platform}-${process.arch}. Bitte die vollständige Erweiterung installieren.`);
      const helper = join(this.plugin.pluginPath(), "native", `${process.platform}-${process.arch}`, "prebuilds", `${process.platform}-${process.arch}`, "spawn-helper");
      if (existsSync(helper)) chmodSync(helper, 0o755);
      const electron = window as unknown as { require: NodeRequire };
      const native = electron.require(entry) as typeof import("node-pty");
      const command = codexCommand({ cwd, profile: selectedProfile, nativeThreadId: this.session.threadId, additionalDirs: [] }, bridge.remote);
      this.fit?.fit();
      this.pty = native.spawn(command.file, command.args, { cwd, env: command.env, name: "xterm-256color", cols: this.term?.cols ?? 100, rows: this.term?.rows ?? 28 });
      this.pty.onData(data => { if (attempt === this.generation) this.term?.write(data); });
      this.pty.onExit(({ exitCode }) => {
        if (attempt !== this.generation) return;
        this.pty = undefined;
        this.plugin.release(this.session.id, this);
        this.bridge?.dispose(); this.bridge = undefined;
        if (this.status) this.status.textContent = `Codex beendet · Exit ${exitCode}`;
        if (this.startButton) { this.startButton.disabled = false; this.startButton.textContent = this.session.threadId ? "Sitzung fortsetzen" : "Codex starten"; }
      });
      this.plugin.saveSession(this.session);
      if (this.profile) this.profile.disabled = true;
      if (this.cwd) this.cwd.disabled = true;
      this.term?.focus();
    } catch (error) {
      if (attempt !== this.generation) return;
      this.plugin.release(this.session.id, this);
      this.bridge?.dispose(); this.bridge = undefined;
      if (this.status) this.status.textContent = error instanceof Error ? error.message : "Codex konnte nicht starten.";
      if (this.startButton) this.startButton.disabled = false;
    } finally { if (attempt === this.generation) this.starting = false; }
  }
  stop(): void {
    ++this.generation;
    this.starting = false;
    this.plugin.release(this.session.id, this);
    this.pty?.kill(); this.pty = undefined;
    this.bridge?.dispose(); this.bridge = undefined;
    if (this.profile) this.profile.disabled = Boolean(this.session.threadId);
    if (this.cwd) this.cwd.disabled = Boolean(this.session.threadId);
    if (this.status) this.status.textContent = "Gestoppt. Eine bestätigte native Sitzung kann wieder aufgenommen werden.";
    if (this.startButton && process.platform === "darwin") { this.startButton.disabled = false; this.startButton.textContent = this.session.threadId ? "Sitzung fortsetzen" : "Codex starten"; }
  }
}
