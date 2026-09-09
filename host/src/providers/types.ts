export type Provider = "claude" | "codex";
export type ReasoningEffort =
  "none" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max" | "ultra";
export type PermissionProfile =
  "read-only" | "workspace-write" | "danger-full-access";
export function providerOf(value: {
  provider?: Provider;
  type?: string;
}): Provider {
  return value.provider === "codex" ? "codex" : "claude";
}
export interface LaunchRequest {
  initialPrompt?: string;
  resumePicker?: boolean;
  provider?: Provider;
  agentName?: string;
  profile?: string;
  cwd: string;
  dangerous?: boolean;
  plain?: boolean;
  nativeThreadId?: string;
  nativeSessionId?: string;
  launchId?: string;
  model?: string;
  reasoningEffort?: ReasoningEffort;
  permissionProfile?: PermissionProfile;
  additionalDirs?: string[];
}
export interface LaunchCommand {
  file: string;
  args: string[];
  cwd: string;
  env: Record<string, string>;
}
export const PROVIDER_LABELS: Record<Provider, string> = {
  claude: "Claude",
  codex: "Codex",
};
