/**
 * S4 command client — Phase 2.
 *
 * `fetch` is injected, so every backend outcome is exercised without a live server and
 * without a DOM. The responses used here are the shapes the running backend was verified
 * to return.
 */

import { describe, expect, it, vi } from "vitest";

import type { CommandRequestPayload } from "../state/dispatchCommand";
import { classifyStatus, submitCommand } from "./commandClient";

const PAYLOAD: CommandRequestPayload = {
  command_id: "CMD-TEST-1",
  vehicle_id: "TRUCK_01",
  action: "STOP",
  target_speed: 0,
  reason: "test",
};

/** A minimal stand-in for the parts of `Response` the client touches. */
function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

function stubFetch(response: Response) {
  return vi.fn(async () => response) as unknown as typeof fetch;
}

// ---------------------------------------------------------------------------
// K — accepted
// ---------------------------------------------------------------------------

describe("accepted command", () => {
  it("K — reports ACCEPTED and carries the backend message verbatim", async () => {
    const fetchImpl = stubFetch(
      jsonResponse(200, {
        command_id: "CMD-TEST-1",
        vehicle_id: "TRUCK_01",
        action: "STOP",
        status: "ACCEPTED",
        timestamp: 1_788_633_778.82,
        message: "Command STOP accepted by gateway for TRUCK_01; not yet executed",
      }),
    );

    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.outcome).toBe("ACCEPTED");
    expect(result.backendStatus).toBe("ACCEPTED");
    expect(result.httpStatus).toBe(200);
    // The backend's own "not yet executed" survives to the operator.
    expect(result.message).toContain("not yet executed");
  });

  it("posts to /api/commands with the exact payload and JSON headers", async () => {
    const fetchImpl = stubFetch(jsonResponse(200, { status: "ACCEPTED", message: "ok" }));
    await submitCommand(PAYLOAD, { fetchImpl });

    const mock = fetchImpl as unknown as ReturnType<typeof vi.fn>;
    const [url, init] = mock.mock.calls[0] as [string, RequestInit];

    expect(url).toContain("/api/commands");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual(PAYLOAD);
  });
});

// ---------------------------------------------------------------------------
// L/M/N — refusals the backend actually returns
// ---------------------------------------------------------------------------

describe("refusals", () => {
  it("L — REJECTED with the fail-closed v_safe message", async () => {
    const fetchImpl = stubFetch(
      jsonResponse(200, {
        status: "REJECTED",
        message: "v_safe unavailable (fail closed)",
      }),
    );
    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.outcome).toBe("REJECTED");
    expect(result.message).toBe("v_safe unavailable (fail closed)");
  });

  it("M — UNKNOWN_VEHICLE", async () => {
    const fetchImpl = stubFetch(
      jsonResponse(200, {
        status: "UNKNOWN_VEHICLE",
        message: "vehicle is not a known physical vehicle",
      }),
    );
    expect((await submitCommand(PAYLOAD, { fetchImpl })).outcome).toBe("UNKNOWN_VEHICLE");
  });

  it("N — DUPLICATE", async () => {
    const fetchImpl = stubFetch(
      jsonResponse(200, {
        status: "DUPLICATE",
        message: "Idempotent replay of an already-accepted command",
      }),
    );
    expect((await submitCommand(PAYLOAD, { fetchImpl })).outcome).toBe("DUPLICATE");
  });
});

// ---------------------------------------------------------------------------
// O/P — HTTP-level refusals
// ---------------------------------------------------------------------------

describe("HTTP-level refusals", () => {
  it("O — HTTP 400 invalid action becomes INVALID with the backend detail", async () => {
    const fetchImpl = stubFetch(
      jsonResponse(400, {
        detail:
          "Invalid action 'LAUNCH'. Must be one of ['TARGET_SPEED', 'HOLD', 'STOP', 'RELEASE']",
      }),
    );
    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.outcome).toBe("INVALID");
    expect(result.httpStatus).toBe(400);
    expect(result.message).toContain("Invalid action");
  });

  it("P — HTTP 422 validation error is summarised readably", async () => {
    const fetchImpl = stubFetch(
      jsonResponse(422, {
        detail: [{ type: "missing", loc: ["body", "command_id"], msg: "Field required" }],
      }),
    );
    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.outcome).toBe("INVALID");
    expect(result.httpStatus).toBe(422);
    expect(result.message).toContain("command_id");
    expect(result.message).toContain("Field required");
  });

  it("handles a 5xx without claiming anything happened", async () => {
    const fetchImpl = stubFetch(jsonResponse(500, { detail: "Internal Server Error" }));
    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.httpStatus).toBe(500);
    expect(result.outcome).not.toBe("ACCEPTED");
  });

  it("handles an error body that is not JSON", async () => {
    const fetchImpl = stubFetch({
      ok: false,
      status: 502,
      json: async () => {
        throw new Error("not json");
      },
    } as unknown as Response);

    const result = await submitCommand(PAYLOAD, { fetchImpl });
    expect(result.outcome).toBe("INVALID");
    expect(result.message).toContain("502");
  });
});

// ---------------------------------------------------------------------------
// Q — transport failure
// ---------------------------------------------------------------------------

describe("transport failure", () => {
  it("Q — a network failure is NETWORK_ERROR, never a success", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error("Failed to fetch");
    }) as unknown as typeof fetch;

    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.outcome).toBe("NETWORK_ERROR");
    expect(result.httpStatus).toBeNull();
    expect(result.message).toContain("Failed to fetch");
  });

  it("an aborted request becomes TIMEOUT, with delivery unconfirmed", async () => {
    const abortError = new Error("aborted");
    abortError.name = "AbortError";
    const fetchImpl = vi.fn(async () => {
      throw abortError;
    }) as unknown as typeof fetch;

    const result = await submitCommand(PAYLOAD, { fetchImpl, timeoutMs: 25 });

    expect(result.outcome).toBe("TIMEOUT");
    expect(result.message).toContain("unconfirmed");
  });

  it("a malformed success body is not read as acceptance", async () => {
    const fetchImpl = stubFetch(jsonResponse(200, { unexpected: true }));
    const result = await submitCommand(PAYLOAD, { fetchImpl });

    expect(result.outcome).toBe("REJECTED");
    expect(result.outcome).not.toBe("ACCEPTED");
    expect(result.message).toContain("did not match");
  });
});

// ---------------------------------------------------------------------------
// status classification
// ---------------------------------------------------------------------------

describe("status classification", () => {
  it.each([
    ["ACCEPTED", "ACCEPTED"],
    ["REJECTED", "REJECTED"],
    ["UNKNOWN_VEHICLE", "UNKNOWN_VEHICLE"],
    ["DUPLICATE", "DUPLICATE"],
    ["INVALID", "INVALID"],
    ["UNSAFE", "UNSAFE"],
    ["TIMEOUT", "TIMEOUT"],
    ["NOT_EXECUTED", "NOT_EXECUTED"],
    ["SUPERSEDED", "NOT_EXECUTED"],
    ["STALE", "REJECTED"],
  ])("maps backend %s to %s", (backend, expected) => {
    expect(classifyStatus(backend)).toBe(expected);
  });

  it("treats an unknown status as REJECTED, never ACCEPTED", () => {
    for (const status of ["WHATEVER", "", null, undefined, "accepted-ish"]) {
      expect(classifyStatus(status), String(status)).toBe("REJECTED");
    }
  });

  it("is case- and whitespace-insensitive", () => {
    expect(classifyStatus("  accepted ")).toBe("ACCEPTED");
  });
});
