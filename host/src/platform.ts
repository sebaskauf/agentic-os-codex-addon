import { homedir } from "os";
import { delimiter, join } from "path";
import { existsSync } from "fs";

export const homeDir = homedir();
// Access is inherited from the member's Codex configuration, never expanded by this host.
export const ALWAYS_ALLOWED_DIRS: string[] = [];
export function spawnEnv(_extra?: unknown, _provider?: string): Record<string, string> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value !== undefined && !key.startsWith("CLAUDECODE") && !key.startsWith("CLAUDE_CODE_")) env[key] = value;
  }
  const dirs = [join(homeDir, ".local", "bin"), "/opt/homebrew/bin", "/usr/local/bin"];
  env.PATH = [...new Set([...(env.PATH ?? "").split(delimiter), ...dirs])].filter(Boolean).join(delimiter);
  return env;
}
export function codexBinary(): string {
  if (process.env.CODEX_BIN) return process.env.CODEX_BIN;
  for (const dir of spawnEnv().PATH.split(delimiter)) {
    const file = join(dir, "codex");
    if (existsSync(file)) return file;
  }
  return "codex";
}
