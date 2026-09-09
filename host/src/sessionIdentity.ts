/** Identity comes exclusively from this TUI's correlated native lifecycle responses. */
export interface SessionMetadata {
  version: 1;
  provider: "codex";
  tabId: string;
  launchId: string;
  nativeThreadId?: string;
  hasUserTurn?: boolean;
  resumeThreadId?: string;
  nativeSessionId?: string;
  model?: string;
  reasoningEffort?: string;
  permissionProfile?: string;
  sandboxMode?: string;
  cwd?: string;
  runtimeWorkspaceRoots?: string[];
  instructionSources?: string[];
  status: "starting" | "ready" | "working" | "idle" | "exited" | "error";
  identityStatus: "pending" | "verified" | "unavailable";
  updatedAt: string;
  exitCode?: number;
  error?: string;
}
type JsonObject = Record<string, unknown>;
function object(v: unknown): v is JsonObject {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}
export function nativeThreadId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(value)
  );
}
export class SessionIdentityObserver {
  private readonly pending = new Map<
    string,
    { method: string; sequence: number }
  >();
  private sequence = 0;
  private selected = 0;
  private disabled = false;
  private metadata: SessionMetadata;
  constructor(
    tabId: string,
    launchId: string,
    private readonly change: (metadata: SessionMetadata) => void,
  ) {
    this.metadata = {
      version: 1,
      provider: "codex",
      tabId,
      launchId,
      status: "starting",
      identityStatus: "pending",
      updatedAt: new Date().toISOString(),
    };
  }
  get current(): SessionMetadata {
    return { ...this.metadata };
  }
  private emit(patch: Partial<SessionMetadata>): void {
    this.metadata = {
      ...this.metadata,
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    this.change(this.current);
  }
  unavailable(reason: string): void {
    this.disabled = true;
    this.pending.clear();
    this.emit({
      identityStatus: "unavailable",
      nativeThreadId: undefined,
      nativeSessionId: undefined,
      // The TUI continues after an observer failure and may accept unseen turns.
      // Never preserve an old "empty thread" assumption for future recovery.
      hasUserTurn: undefined,
      error: reason,
    });
  }
  request(v: unknown): void {
    if (
      this.disabled ||
      !object(v) ||
      !(typeof v.id === "string" || typeof v.id === "number") ||
      typeof v.method !== "string"
    )
      return;
    if (["thread/start", "thread/resume", "thread/fork"].includes(v.method)) {
      if (this.pending.size > 100) {
        this.unavailable("Zu viele offene native Sessionwechsel");
        return;
      }
      this.pending.set(String(v.id), {
        method: v.method,
        sequence: ++this.sequence,
      });
      this.selected = this.sequence;
    }
  }
  response(v: unknown): void {
    if (this.disabled || !object(v)) return;
    if (typeof v.id === "string" || typeof v.id === "number") {
      const request = this.pending.get(String(v.id));
      if (request) {
        this.pending.delete(String(v.id));
        if (request.sequence !== this.selected) return;
        if (v.error !== undefined) {
          this.emit({ error: "Nativer Sessionwechsel fehlgeschlagen" });
          return;
        }
        const result = v.result;
        if (
          !object(result) ||
          !object(result.thread) ||
          !nativeThreadId(result.thread.id)
        ) {
          this.unavailable(
            "Native Sessionantwort enthält keine eindeutige Thread-ID",
          );
          return;
        }
        this.emit({
          nativeThreadId: result.thread.id,
          hasUserTurn:
            request.method === "thread/resume" ||
            request.method === "thread/fork",
          nativeSessionId:
            typeof result.thread.sessionId === "string"
              ? result.thread.sessionId
              : undefined,
          model:
            typeof result.model === "string"
              ? result.model
              : this.metadata.model,
          reasoningEffort:
            typeof result.reasoningEffort === "string"
              ? result.reasoningEffort
              : this.metadata.reasoningEffort,
          permissionProfile:
            object(result.activePermissionProfile) &&
            typeof result.activePermissionProfile.id === "string"
              ? result.activePermissionProfile.id
              : undefined,
          sandboxMode:
            object(result.sandbox) && typeof result.sandbox.type === "string"
              ? result.sandbox.type
              : undefined,
          cwd: typeof result.cwd === "string" ? result.cwd : undefined,
          runtimeWorkspaceRoots: Array.isArray(result.runtimeWorkspaceRoots)
            ? result.runtimeWorkspaceRoots.filter(
                (v): v is string => typeof v === "string",
              )
            : undefined,
          instructionSources: Array.isArray(result.instructionSources)
            ? result.instructionSources.filter(
                (v): v is string => typeof v === "string",
              )
            : undefined,
          status: "ready",
          identityStatus: "verified",
          error: undefined,
        });
        return;
      }
    }
    if (!object(v.params) || v.params.threadId !== this.metadata.nativeThreadId)
      return;
    if (v.method === "turn/started")
      this.emit({ status: "working", hasUserTurn: true });
    if (v.method === "turn/completed") this.emit({ status: "idle" });
    if (
      v.method === "thread/settings/updated" &&
      object(v.params.threadSettings)
    ) {
      const settings = v.params.threadSettings;
      this.emit({
        model:
          typeof settings.model === "string"
            ? settings.model
            : this.metadata.model,
        reasoningEffort:
          typeof settings.effort === "string"
            ? settings.effort
            : this.metadata.reasoningEffort,
        permissionProfile:
          object(settings.activePermissionProfile) &&
          typeof settings.activePermissionProfile.id === "string"
            ? settings.activePermissionProfile.id
            : this.metadata.permissionProfile,
        sandboxMode:
          object(settings.sandboxPolicy) &&
          typeof settings.sandboxPolicy.type === "string"
            ? settings.sandboxPolicy.type
            : this.metadata.sandboxMode,
      });
    }
  }
  exit(code: number, error?: string): void {
    this.emit({ status: error ? "error" : "exited", exitCode: code, error });
  }
}
/** Passive RFC 6455 reader. Never rewrites bytes. Fragmented/masked frames are supported. */
export class WebSocketJsonObserver {
  private buffer = Buffer.alloc(0);
  private upgrade = true;
  private fragments: Buffer[] = [];
  private size = 0;
  private disabled = false;
  constructor(
    private readonly message: (value: unknown) => void,
    private readonly invalid: (reason: string) => void,
    private readonly limit = 8 * 1024 * 1024,
  ) {}
  push(chunk: Buffer): void {
    if (this.disabled) return;
    this.buffer = Buffer.concat([this.buffer, chunk]);
    if (this.buffer.length > this.limit) {
      this.fail(
        "Native Protokollnachricht überschreitet das Beobachtungslimit",
      );
      return;
    }
    if (this.upgrade) {
      const index = this.buffer.indexOf("\r\n\r\n");
      if (index < 0) return;
      const headers = this.buffer.subarray(0, index).toString();
      if (/Sec-WebSocket-Extensions:/i.test(headers)) {
        this.fail("Komprimierte native WebSocket-Verbindung nicht unterstützt");
        return;
      }
      this.buffer = this.buffer.subarray(index + 4);
      this.upgrade = false;
    }
    while (this.buffer.length >= 2) {
      const first = this.buffer[0]!,
        second = this.buffer[1]!;
      const final = (first & 128) !== 0,
        opcode = first & 15,
        masked = (second & 128) !== 0;
      let size = second & 127,
        offset = 2;
      if (first & 112) {
        this.fail("Unbekannte WebSocket-Erweiterung");
        return;
      }
      if (size === 126) {
        if (this.buffer.length < 4) return;
        size = this.buffer.readUInt16BE(2);
        offset = 4;
      } else if (size === 127) {
        if (this.buffer.length < 10) return;
        const length = this.buffer.readBigUInt64BE(2);
        if (length > BigInt(this.limit)) {
          this.fail("Native Protokollnachricht zu groß");
          return;
        }
        size = Number(length);
        offset = 10;
      }
      if (size > this.limit) {
        this.fail("Native Protokollnachricht zu groß");
        return;
      }
      const maskOffset = offset;
      offset += masked ? 4 : 0;
      if (this.buffer.length < offset + size) return;
      const payload = Buffer.from(this.buffer.subarray(offset, offset + size));
      if (masked)
        for (let i = 0; i < payload.length; i++)
          payload[i] = payload[i]! ^ this.buffer[maskOffset + (i % 4)]!;
      this.buffer = this.buffer.subarray(offset + size);
      if (opcode >= 8) continue;
      if (opcode === 1) {
        this.fragments = [];
        this.size = 0;
      } else if (opcode !== 0) {
        this.fail("Unbekannter WebSocket-Datentyp");
        return;
      }
      this.fragments.push(payload);
      this.size += size;
      if (this.size > this.limit) {
        this.fail("Fragmentierte native Nachricht zu groß");
        return;
      }
      if (final) {
        const text = Buffer.concat(this.fragments).toString("utf8");
        this.fragments = [];
        this.size = 0;
        try {
          this.message(JSON.parse(text));
        } catch {
          this.fail("Native Protokollantwort ist kein JSON");
          return;
        }
      }
    }
  }
  private fail(reason: string): void {
    this.disabled = true;
    this.buffer = Buffer.alloc(0);
    this.fragments = [];
    this.invalid(reason);
  }
}
