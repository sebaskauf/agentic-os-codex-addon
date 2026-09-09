import { nativeThreadId, type SessionMetadata } from "./sessionIdentity";
export interface SavedSession {
  id: string;
  cwd: string;
  profile?: string;
  threadId?: string;
}
export interface HostSettings { enabled: boolean; sessions: SavedSession[]; }
export function readSettings(value: unknown): HostSettings {
  if (!value || typeof value !== "object") return { enabled: false, sessions: [] };
  const data = value as Record<string, unknown>;
  const sessions: SavedSession[] = [];
  for (const candidate of Array.isArray(data.sessions) ? data.sessions : []) {
    if (!candidate || typeof candidate !== "object") continue;
    const item = candidate as Record<string, unknown>;
    if (typeof item.id !== "string" || typeof item.cwd !== "string") continue;
    const profile = typeof item.profile === "string" && /^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(item.profile) ? item.profile : undefined;
    sessions.push({ id: item.id, cwd: item.cwd, profile, threadId: nativeThreadId(item.threadId) ? item.threadId : undefined });
  }
  return { enabled: data.enabled === true, sessions };
}

/** Empty freshly started threads are not necessarily persisted by Codex yet. */
export function resumableThread(metadata: SessionMetadata): string | undefined {
  return metadata.identityStatus === "verified" && metadata.hasUserTurn === true && nativeThreadId(metadata.nativeThreadId) ? metadata.nativeThreadId : undefined;
}
