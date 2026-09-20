import { homedir } from "os";
import { delimiter, join } from "path";
import { existsSync } from "fs";

export const homeDir = homedir();
export const isWin = process.platform === "win32";
/** Codex host processes are supported on macOS and Windows; Linux has no packaged terminal yet. */
export function supportedPlatform(): boolean {
  return process.platform === "darwin" || process.platform === "win32";
}
// Access is inherited from the member's Codex configuration, never expanded by this host.
export const ALWAYS_ALLOWED_DIRS: string[] = [];

function envKey(env: Record<string, string>, name: string): string {
  if (!isWin) return name;
  const lower = name.toLowerCase();
  return Object.keys(env).find((key) => key.toLowerCase() === lower) ?? name;
}

function extraDirs(): string[] {
  if (isWin) {
    const local = process.env.LOCALAPPDATA ?? join(homeDir, "AppData", "Local");
    const roaming = process.env.APPDATA ?? join(homeDir, "AppData", "Roaming");
    return [
      join(roaming, "npm"),
      join(local, "Programs", "codex", "bin"),
      join(local, "Microsoft", "WinGet", "Links"),
      join(homeDir, ".local", "bin"),
    ];
  }
  return [join(homeDir, ".local", "bin"), "/opt/homebrew/bin", "/usr/local/bin"];
}

export function spawnEnv(_extra?: unknown, _provider?: string): Record<string, string> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value !== undefined && !key.startsWith("CLAUDECODE") && !key.startsWith("CLAUDE_CODE_")) env[key] = value;
  }
  const key = envKey(env, "PATH");
  env[key] = [...new Set([...(env[key] ?? "").split(delimiter), ...extraDirs()])].filter(Boolean).join(delimiter);
  if (key !== "PATH") env.PATH = env[key];
  return env;
}

function npmCodexExe(): string | undefined {
  if (!isWin) return undefined;
  const roaming = process.env.APPDATA ?? join(homeDir, "AppData", "Roaming");
  const triple = process.arch === "arm64" ? "aarch64-pc-windows-msvc" : "x86_64-pc-windows-msvc";
  const pkg = join(roaming, "npm", "node_modules", "@openai", "codex");
  const candidates = [
    join(pkg, "node_modules", "@openai", `codex-win32-${process.arch}`, "vendor", triple, "bin", "codex.exe"),
    join(roaming, "npm", "node_modules", "@openai", `codex-win32-${process.arch}`, "vendor", triple, "bin", "codex.exe"),
    join(pkg, "vendor", triple, "codex", "codex.exe"),
    join(pkg, "bin", "codex.exe"),
  ];
  return candidates.find((file) => existsSync(file));
}

/** Resolve the Codex executable. Windows prefers the real .exe over the npm .cmd shim. */
export function codexBinary(): string {
  if (process.env.CODEX_BIN) return process.env.CODEX_BIN;
  if (process.env.CODEX_CLI_PATH && existsSync(process.env.CODEX_CLI_PATH)) return process.env.CODEX_CLI_PATH;
  const names = isWin ? ["codex.exe", "codex.cmd", "codex.bat"] : ["codex"];
  const env = spawnEnv();
  const path = env[envKey(env, "PATH")] ?? "";
  let shim: string | undefined;
  for (const dir of path.split(delimiter)) {
    if (!dir) continue;
    for (const name of names) {
      const file = join(dir, name);
      if (!existsSync(file)) continue;
      if (name === "codex.exe" || !isWin) return file;
      shim ??= file;
    }
  }
  const exe = npmCodexExe();
  if (exe) return exe;
  if (shim) return shim;
  return isWin ? "codex.cmd" : "codex";
}

function quoteCmdArg(value: string): string {
  if (/[\r\n]/.test(value)) throw new Error("Zeilenumbrüche sind in Startargumenten nicht erlaubt");
  if (value.includes('"')) throw new Error("Anführungszeichen sind in Startargumenten nicht erlaubt");
  return /[\s&|<>^()]/.test(value) || value === "" ? `"${value}"` : value;
}

/**
 * Windows cannot execute npm .cmd/.bat shims directly (spawn EINVAL); they need cmd.exe.
 * Everything else is returned unchanged.
 */
export function wrapForCmd(file: string, args: string[], comSpec = process.env.ComSpec ?? "cmd.exe"): { file: string; args: string[] } {
  const line = [file, ...args].map(quoteCmdArg).join(" ");
  return { file: comSpec, args: ["/d", "/s", "/c", `"${line}"`] };
}
export function spawnable(file: string, args: string[]): { file: string; args: string[] } {
  if (!isWin || !/\.(cmd|bat)$/i.test(file)) return { file, args };
  return wrapForCmd(file, args);
}
