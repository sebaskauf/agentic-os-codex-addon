import { setTimeout as nodeSetTimeout } from "timers";
import { spawn, type ChildProcess } from "child_process";
import { chmodSync, existsSync, mkdtempSync, writeFileSync } from "fs";
import { createServer, connect, type Socket, type Server } from "net";
import { randomBytes } from "crypto";
import { tmpdir } from "os";
import { join } from "path";
import {
  SessionIdentityObserver,
  WebSocketJsonObserver,
  type SessionMetadata,
} from "./sessionIdentity";
import { codexBinary, isWin, spawnEnv, spawnable } from "./platform";
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
  /** Extra environment for the TUI (auth token variable on the websocket transport). */
  tuiEnv: Record<string, string>;
  /** Extra TUI arguments (auth token reference on the websocket transport). */
  tuiArgs: string[];
  transport: "unix" | "ws";
}
export const TOKEN_ENV = "AGENTIC_OS_CODEX_TOKEN";
/**
 * macOS uses a private Unix socket pair. Windows has no Unix-socket support in Node's
 * Electron renderer path, so it uses loopback WebSocket ports guarded by a capability
 * token that only this process and its TUI know. Set AGENTIC_OS_CODEX_TRANSPORT=ws to
 * exercise the Windows path on macOS.
 */
export function bridgeTransport(): "unix" | "ws" {
  if (process.env.AGENTIC_OS_CODEX_TRANSPORT === "ws") return "ws";
  if (process.env.AGENTIC_OS_CODEX_TRANSPORT === "unix") return "unix";
  return isWin ? "ws" : "unix";
}
function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      const port = typeof address === "object" && address ? address.port : 0;
      probe.close(() => (port ? resolve(port) : reject(new Error("Kein freier Port"))));
    });
  });
}
function portReady(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = connect(port, "127.0.0.1");
    socket.once("connect", () => { socket.destroy(); resolve(true); });
    socket.once("error", () => resolve(false));
  });
}
function killTree(child: ChildProcess): void {
  if (child.pid === undefined) return;
  if (isWin) {
    try { spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore", windowsHide: true }); } catch {}
    return;
  }
  try { process.kill(-child.pid, "SIGTERM"); } catch {}
  const timer = nodeSetTimeout(() => { try { process.kill(-child.pid!, "SIGKILL"); } catch {} }, 2500);
  timer.unref();
}
/** Own server per TUI: no calls are injected and no other local sessions are controlled. */
export async function startCodexBridge(
  opts: CodexBridgeOptions,
): Promise<CodexBridge> {
  const transport = bridgeTransport();
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
  // Unix sockets need short paths (104 bytes on macOS), so /tmp stays the socket root there.
  const root = transport === "unix" ? mkdtempSync("/tmp/aos-codex-") : mkdtempSync(join(tmpdir(), "aos-codex-"));
  if (!isWin) chmodSync(root, 0o700);
  const front = join(root, "tui.sock");
  const back = join(root, "server.sock");
  const tuiEnv: Record<string, string> = {};
  const tuiArgs: string[] = [];
  let backPort = 0;
  let frontPort = 0;
  const listenArgs: string[] = [];
  if (transport === "ws") {
    backPort = await freePort();
    frontPort = await freePort();
    const token = randomBytes(32).toString("hex");
    const tokenFile = join(root, "token");
    writeFileSync(tokenFile, token + "\n", { mode: 0o600 });
    listenArgs.push("--listen", `ws://127.0.0.1:${backPort}`, "--ws-auth", "capability-token", "--ws-token-file", tokenFile);
    tuiEnv[TOKEN_ENV] = token;
    tuiArgs.push("--remote-auth-token-env", TOKEN_ENV);
  } else {
    listenArgs.push("--listen", `unix://${back}`);
  }
  const launch = spawnable(codexBinary(), ["app-server", ...listenArgs, ...overrides]);
  const child = spawn(launch.file, launch.args, {
    cwd: opts.cwd,
    env: {
      ...spawnEnv(undefined, "codex"),
      AGENTIC_OS_TAB_ID: opts.tabId,
      AGENTIC_OS_LAUNCH_ID: opts.launchId,
    },
    detached: !isWin,
    windowsHide: true,
    stdio: ["ignore", "ignore", "pipe"],
  });
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
  const server: Server = createServer((client) => {
    if (connected || closed) {
      client.destroy();
      return;
    }
    connected = true;
    sockets.add(client);
    const backend = transport === "ws" ? connect(backPort, "127.0.0.1") : connect(back);
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
    killTree(child);
  };
  try {
    await new Promise<void>((resolve, reject) => {
      const deadline = Date.now() + 15000;
      const check = async (): Promise<void> => {
        if (failure !== undefined) {
          reject(new Error(failure));
          return;
        }
        const ready = transport === "ws" ? await portReady(backPort) : existsSync(back);
        if (ready) {
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
        nodeSetTimeout(() => void check(), 50);
      };
      void check();
    });
    await new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      if (transport === "ws") {
        server.listen(frontPort, "127.0.0.1", () => resolve());
      } else {
        server.listen(front, () => {
          chmodSync(front, 0o600);
          resolve();
        });
      }
    });
    const remote = transport === "ws" ? `ws://127.0.0.1:${frontPort}` : `unix://${front}`;
    return { remote, dispose, identity, tuiEnv, tuiArgs, transport };
  } catch (error) {
    dispose();
    throw error;
  }
}
