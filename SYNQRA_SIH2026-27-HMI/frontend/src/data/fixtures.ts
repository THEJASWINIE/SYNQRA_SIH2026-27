/**
 * Fixture loading for tests — M2.
 *
 * Reads the cross-language fixtures in `contracts/fixtures/` (MAD-C), the same files the
 * Python parity test reads. Test-support only; nothing in the application imports this.
 */

import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import type { MessageType } from "../contracts/raw";

const FIXTURE_ROOT = join(process.cwd(), "..", "contracts", "fixtures");

export function loadValid(messageType: MessageType): unknown {
  return JSON.parse(readFileSync(join(FIXTURE_ROOT, "valid", `${messageType}.json`), "utf-8"));
}

/** Fixture files are named `<MessageType>__<case>.json`. */
export interface NamedFixture {
  file: string;
  messageType: MessageType;
  payload: unknown;
}

function loadDir(dir: string): NamedFixture[] {
  return readdirSync(join(FIXTURE_ROOT, dir))
    .filter((f) => f.endsWith(".json"))
    .map((file) => {
      const messageType = file.split("__")[0] as MessageType;
      const payload: unknown = JSON.parse(readFileSync(join(FIXTURE_ROOT, dir, file), "utf-8"));
      return { file, messageType, payload };
    });
}

export const loadInvalid = (): NamedFixture[] => loadDir("invalid");
export const loadUnknownEnum = (): NamedFixture[] => loadDir("unknown-enum");
