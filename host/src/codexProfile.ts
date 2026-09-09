import { readFileSync } from "fs";
import { join } from "path";
import { parse } from "./vendor/smol-toml/dist/index";
import { codexHome, validateCodexProfile } from "./providers/codex";
function toml(value: unknown): string {
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return `[${value.map(toml).join(",")}]`;
  if (value instanceof Date) return value.toISOString();
  if (value !== null && typeof value === "object")
    return `{${Object.entries(value)
      .map(([key, v]) => `${JSON.stringify(key)}=${toml(v)}`)
      .join(",")}}`;
  throw new Error("Nicht unterstützter TOML-Wert im Codex-Profil");
}
/** app-server has no -p. Parse the original native layer and pass equivalent native -c values. */
export function profileOverrides(profile?: string): string[] {
  if (profile === undefined) return [];
  validateCodexProfile(profile);
  const parsed = parse(
    readFileSync(join(codexHome(), `${profile}.config.toml`), "utf8"),
  );
  const result: string[] = [];
  const visit = (value: unknown, keys: string[]): void => {
    if (
      value !== null &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      !(value instanceof Date)
    ) {
      for (const [key, child] of Object.entries(value))
        visit(child, [...keys, key]);
      return;
    }
    result.push(
      "-c",
      `${keys
        .map((key) => {
          if (!/^[A-Za-z0-9_-]+$/.test(key))
            throw new Error(
              "Nicht unterstützter Konfigurationsschlüssel im Codex-Profil",
            );
          return key;
        })
        .join(".")}=${toml(value)}`,
    );
  };
  for (const [key, value] of Object.entries(parsed)) visit(value, [key]);
  return result;
}
