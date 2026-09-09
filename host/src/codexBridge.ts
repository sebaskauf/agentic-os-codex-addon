import { setTimeout as nodeSetTimeout } from "timers";
import { spawn, type ChildProcess } from "child_process";
import { chmodSync, existsSync, mkdtempSync } from "fs";
import { createServer, connect, type Socket } from "net";
import { join } from "path";
import {
  SessionIdentityObserver,
  WebSocketJsonObserver,
  type SessionMetadata,
} from "./sessionIdentity";
import { codexBinary, spawnEnv } from "./platform";
import { profileOverrides } from "./codexProfile";
export interface CodexBridgeOptions {
  tabId: string;
  launchId: string;
  profile?: string;
  cwd: string;
  onMetadata: (metadata: SessionMetadata) => void;
}
export interface CodexBridge {
  remote: string;
  dispose: () => void;
  identity: SessionIdentityObserver;
}
/** Own server per TUI: no calls are injected and no other local sessions are controlled. */
export async function startCodexBridge(
  opts: CodexBridgeOptions,
): Promise<CodexBridge> {
  if (process.platform === "win32")
    throw new Error(
      "Codex-Identitätsbridge benötigt Unix-Sockets auf diesem Host",
    );
  const root = mkdtempSync("/tmp/aos-codex-");
  chmodSync(root, 0o700);
  const front = join(root, "tui.sock"),
    back = join(root, "server.sock");
  const identity = new SessionIdentityObserver(
    opts.tabId,
    opts.launchId,
    opts.onMetadata,
  );
  const sockets = new Set<Socket>();
  let closed = false;
  let connected = false;
  let failure: string | undefined;
  const overrides = profileOverrides(opts.profile);
  const child = spawn(
    codexBinary(),
    ["app-server", "--listen", `unix://${back}`, ...overrides],
    {
      cwd: opts.cwd,
      env: {
        ...spawnEnv(undefined, "codex"),
        AGENTIC_OS_TAB_ID: opts.tabId,
        AGENTIC_OS_LAUNCH_ID: opts.launchId,
      },
      detached: true,
      stdio: ["ignore", "ignore", "pipe"],
    },
  );
  // Diagnostics can contain file paths/config details. Keep a bounded private summary only.
  let diagnostics = "";
  child.stderr?.on("data", (chunk: Buffer) => {
    diagnostics = (diagnostics + chunk.toString()).slice(-2048);
  });
  child.on("error", (error: Error) => {
    failure = error.message;
    identity.exit(1, "Codex-App-Server konnte nicht starten");
  });
  child.on("exit", (code: number | null) => {
    if (!closed) {
      failure = `Codex-App-Server beendet (${code ?? 1})`;
      identity.exit(code ?? 1, failure);
      for (const socket of sockets) socket.destroy();
    }
  });
  const server = createServer((client) => {
    if (connected || closed) {
      client.destroy();
      return;
    }
    connected = true;
    sockets.add(client);
    const backend = connect(back);
    sockets.add(backend);
    const clientObserver = new WebSocketJsonObserver(
      (value) => identity.request(value),
      (reason) => identity.unavailable(reason),
    );
    const serverObserver = new WebSocketJsonObserver(
      (value) => identity.response(value),
      (reason) => identity.unavailable(reason),
    );
    client.on("data", (chunk: Buffer) => clientObserver.push(chunk));
    backend.on("data", (chunk: Buffer) => serverObserver.push(chunk));
    client.pipe(backend);
    backend.pipe(client);
    client.on("error", () => backend.destroy());
    backend.on("error", () => {
      identity.unavailable(
        "Verbindung zum eigenen Codex-App-Server unterbrochen",
      );
      client.destroy();
    });
    client.on("close", () => {
      backend.destroy();
      dispose();
    });
  });
  const dispose = (): void => {
    if (closed) return;
    closed = true;
    for (const socket of sockets) socket.destroy();
    server.close();
    try {
      if (child.pid !== undefined) process.kill(-child.pid, "SIGTERM");
    } catch {}
    const timer = nodeSetTimeout(() => {
      try {
        if (child.pid !== undefined) process.kill(-child.pid, "SIGKILL");
      } catch {}
    }, 2500);
    timer.unref();
  };
  try {
    await new Promise<void>((resolve, reject) => {
      const deadline = Date.now() + 15000;
      const check = (): void => {
        if (failure !== undefined) {
          reject(new Error(failure));
          return;
        }
        if (existsSync(back)) {
          resolve();
          return;
        }
        if (Date.now() > deadline) {
          reject(
            new Error(
              "Codex-App-Server startet nicht innerhalb von 15 Sekunden",
            ),
          );
          return;
        }
        nodeSetTimeout(check, 50);
      };
      check();
    });
    await new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      server.listen(front, () => {
        chmodSync(front, 0o600);
        resolve();
      });
    });
    return { remote: `unix://${front}`, dispose, identity };
  } catch (error) {
    dispose();
    throw error;
  }
}
