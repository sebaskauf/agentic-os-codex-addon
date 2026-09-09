import { existsSync, readdirSync } from "fs";
import { join } from "path";
import {
  ALWAYS_ALLOWED_DIRS,
  codexBinary,
  homeDir,
  spawnEnv,
} from "../platform";
import type { LaunchCommand, LaunchRequest } from "./types";
export const CODEX_COMMANDS = [
  "/model",
  "/permissions",
  "/status",
  "/usage",
  "/plugins",
  "/skills",
  "/mcp",
  "/compact",
  "/resume",
] as const;
export function codexHome(): string {
  return process.env.CODEX_HOME ?? join(homeDir, ".codex");
}
export function listCodexProfiles(): string[] {
  try {
    return readdirSync(codexHome())
      .filter((n) => /^[A-Za-z0-9][A-Za-z0-9_-]*\.config\.toml$/.test(n))
      .map((n) => n.slice(0, -12))
      .sort();
  } catch {
    return [];
  }
}
export function validateCodexProfile(profile: string): void {
  if (
    !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(profile) ||
    !existsSync(join(codexHome(), `${profile}.config.toml`))
  )
    throw new Error(`Codex-Profil fehlt: ${profile}`);
}
export function codexCommand(
  request: LaunchRequest,
  remote?: string,
): LaunchCommand {
  const args: string[] = [];
  const profile = request.profile ?? request.agentName;
  if (profile !== undefined) {
    validateCodexProfile(profile);
    args.push("-p", profile);
  }
  if (remote !== undefined) args.push("--remote", remote);
  args.push("--no-alt-screen", "-C", request.cwd);
  const dirs = new Set(request.additionalDirs ?? ALWAYS_ALLOWED_DIRS);
  dirs.delete(request.cwd);
  dirs.delete(homeDir);
  for (const dir of dirs) args.push("--add-dir", dir);
  if (request.model !== undefined) args.push("--model", request.model);
  if (request.reasoningEffort !== undefined)
    args.push(
      "-c",
      `model_reasoning_effort=${JSON.stringify(request.reasoningEffort)}`,
    );
  if (request.permissionProfile !== undefined)
    args.push("--sandbox", request.permissionProfile);
  // Claude's legacy dangerous boolean deliberately has no Codex meaning.
  if (request.resumePicker === true && request.nativeThreadId === undefined)
    args.push("resume");
  if (request.nativeThreadId !== undefined) {
    if (
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        request.nativeThreadId,
      )
    )
      throw new Error("Ungültige Codex-Thread-ID");
    args.push("resume", request.nativeThreadId);
  }
  if (
    request.initialPrompt !== undefined &&
    request.nativeThreadId === undefined &&
    request.resumePicker !== true
  )
    args.push("--", request.initialPrompt);
  return {
    file: codexBinary(),
    args,
    cwd: request.cwd,
    env: spawnEnv(undefined, "codex"),
  };
}
