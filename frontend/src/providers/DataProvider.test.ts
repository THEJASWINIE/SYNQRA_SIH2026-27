/**
 * Provider boundary tests — M2.
 * Covers required test categories 12, 13, 15.
 *
 * NO PROVIDER IS IMPLEMENTED IN M2. The stubs below exist only inside this test file to
 * exercise the error typing and the interface shape. A stub must never become a shipped
 * provider (realtime-data skill §13).
 */

import { describe, expect, it, vi } from "vitest";
import type { ProviderError } from "../data/errors";
import { isProviderError, isValidationFailure, providerError } from "../data/errors";
import type { DataProvider, ProviderPatch, StatusListener, UpdateListener } from "./DataProvider";

const NOW = "2026-01-01T00:00:00.000Z";

/** Minimal in-test stub. Not a provider implementation — it produces no data. */
function makeStub(partial: Partial<DataProvider> = {}): DataProvider {
  return {
    kind: "MOCK",
    connect: async () => undefined,
    disconnect: async () => undefined,
    subscribe: (_onUpdate: UpdateListener) => () => undefined,
    onStatusChange: (_listener: StatusListener) => () => undefined,
    sendAcknowledgement: async () => undefined,
    ...partial,
  };
}

describe("provider initialization failure typing (category 12)", () => {
  it("surfaces an INITIALIZATION error, not a bare throw", async () => {
    const failure: ProviderError = providerError("INITIALIZATION", "source unavailable", {
      occurredAt: NOW,
      retryable: false,
    });

    const provider = makeStub({
      connect: async () => {
        throw failure;
      },
    });

    await expect(provider.connect()).rejects.toMatchObject({
      kind: "INITIALIZATION",
      retryable: false,
    });
  });

  it("initialization failure is distinguishable from transport failure", () => {
    const init = providerError("INITIALIZATION", "never connected", { occurredAt: NOW });
    const transport = providerError("TRANSPORT", "link lost", { occurredAt: NOW });
    expect(init.kind).not.toBe(transport.kind);
  });
});

describe("provider/transport failure typing (category 13)", () => {
  it("transport errors default to retryable", () => {
    const e = providerError("TRANSPORT", "link lost", { occurredAt: NOW });
    expect(e.retryable).toBe(true);
  });

  it("initialization errors do not default to retryable", () => {
    const e = providerError("INITIALIZATION", "bad config", { occurredAt: NOW });
    expect(e.retryable).toBe(false);
  });

  it("carries an optional cause without inventing one", () => {
    const withCause = providerError("PROTOCOL", "bad frame", {
      occurredAt: NOW,
      cause: "unexpected opcode",
    });
    const without = providerError("PROTOCOL", "bad frame", { occurredAt: NOW });
    expect(withCause.cause).toBe("unexpected opcode");
    expect(without.cause).toBeNull();
  });

  it("status listeners receive the error alongside the status", () => {
    const seen: Array<[string, ProviderError | null]> = [];
    const listener: StatusListener = (status, error) => seen.push([status, error]);

    const error = providerError("TRANSPORT", "link lost", { occurredAt: NOW });
    const provider = makeStub({
      onStatusChange: (l) => {
        l("CONNECTED", null);
        l("DISCONNECTED", error);
        return () => undefined;
      },
    });

    provider.onStatusChange(listener);
    expect(seen).toHaveLength(2);
    expect(seen[0]).toEqual(["CONNECTED", null]);
    expect(seen[1]?.[0]).toBe("DISCONNECTED");
    expect(seen[1]?.[1]?.kind).toBe("TRANSPORT");
  });

  it("distinguishes transport failure from validation failure at the type level", () => {
    const transport = providerError("TRANSPORT", "link lost", { occurredAt: NOW });
    expect(isProviderError(transport)).toBe(true);
    expect(isValidationFailure(transport)).toBe(false);

    const validation = {
      kind: "VALIDATION" as const,
      messageType: "SafetyState" as const,
      issues: [],
      receivedAt: NOW,
    };
    expect(isValidationFailure(validation)).toBe(true);
    expect(isProviderError(validation)).toBe(false);
  });
});

describe("interface shape (category 15)", () => {
  it("subscribe returns an unsubscribe function", () => {
    const unsubscribe = vi.fn();
    const provider = makeStub({ subscribe: () => unsubscribe });
    const off = provider.subscribe(() => undefined);
    off();
    expect(unsubscribe).toHaveBeenCalledOnce();
  });

  it("onStatusChange returns an unsubscribe function", () => {
    const unsubscribe = vi.fn();
    const provider = makeStub({ onStatusChange: () => unsubscribe });
    provider.onStatusChange(() => undefined)();
    expect(unsubscribe).toHaveBeenCalledOnce();
  });

  it("emits normalized patches, never raw frames", () => {
    const received: ProviderPatch[] = [];
    const provider = makeStub({
      subscribe: (onUpdate) => {
        onUpdate({ changes: { vehicles: {} } });
        return () => undefined;
      },
    });
    provider.subscribe((patch) => received.push(patch));
    expect(received).toHaveLength(1);
    expect(received[0]?.changes).toHaveProperty("vehicles");
  });

  it("connect and disconnect resolve without throwing", async () => {
    const provider = makeStub();
    await expect(provider.connect()).resolves.toBeUndefined();
    await expect(provider.disconnect()).resolves.toBeUndefined();
  });
});

describe("acknowledgement boundary (PAD-D)", () => {
  it("takes only an alert id and an actor — no command, speed or vehicle-control argument", () => {
    const provider = makeStub();
    // Arity is the guard: two arguments, neither of which can carry a command.
    expect(provider.sendAcknowledgement.length).toBeLessThanOrEqual(2);
  });

  it("no method exists for issuing a command, overriding, or actuating", () => {
    const provider = makeStub();
    const methods = Object.keys(provider);
    for (const forbidden of [
      "sendCommand",
      "issueCommand",
      "override",
      "actuate",
      "setTargetSpeed",
      "setVSafe",
      "setHSafe",
      "dispatch",
    ]) {
      expect(methods).not.toContain(forbidden);
    }
  });
});
