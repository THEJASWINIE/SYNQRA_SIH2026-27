/**
 * Phase 10 — Failure Injection / Demo Lab tests.
 *
 * Tests the screen rendering (using react-dom/server per M4D-C) and the pure evaluators
 * and scenario runners in demoLabClient.
 */

import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  SCENARIOS,
  createScenarioRunners,
  demoId,
  demoSequence,
  evaluateCommandStatus,
  evaluateCounterDelta,
  evaluateHttpRejection,
} from "../api/demoLabClient";
import { FailureInjectionLab } from "./FailureInjectionLab";

/** Colour is stripped before assertion, so nothing can pass on colour alone (NFR-008). */
function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

describe("FailureInjectionLab screen rendering (Phase 10)", () => {
  it("renders without errors", () => {
    const html = greyscale(renderToString(<FailureInjectionLab />));
    expect(html).toContain("Failure Injection / Demo Lab");
  });

  it("prominently displays the SIMULATION / TEST ONLY banner", () => {
    const html = greyscale(renderToString(<FailureInjectionLab />));
    expect(html).toContain("SIMULATION / TEST ONLY — NOT A PRODUCTION CONTROL");
    expect(html).toContain("No physical vehicle control is performed by this panel");
  });

  it("renders all 10 scenario titles", () => {
    const html = greyscale(renderToString(<FailureInjectionLab />));
    for (const scenario of SCENARIOS) {
      expect(html).toContain(scenario.title);
    }
  });

  it("renders Run All and Reset Demo buttons", () => {
    const html = greyscale(renderToString(<FailureInjectionLab />));
    expect(html).toContain("Run All");
    expect(html).toContain("Reset Demo");
  });

  it("renders empty event log state initially", () => {
    const html = greyscale(renderToString(<FailureInjectionLab />));
    expect(html).toContain("NO INJECTIONS YET");
  });
});

describe("demoLabClient pure evaluators (Phase 10)", () => {
  it("evaluateHttpRejection returns PASS when status matches expected", () => {
    const result = evaluateHttpRejection(400, 400, "Bad Request");
    expect(result.status).toBe("PASS");
    expect(result.expected).toBe("HTTP 400");
    expect(result.observed).toBe("HTTP 400");
    expect(result.evidence).toContain("Backend rejected with 400");
  });

  it("evaluateHttpRejection returns FAIL when status differs", () => {
    const result = evaluateHttpRejection(200, 400, "Ingested");
    expect(result.status).toBe("FAIL");
    expect(result.expected).toBe("HTTP 400");
    expect(result.observed).toBe("HTTP 200");
    expect(result.evidence).toContain("Expected HTTP 400, got 200");
  });

  it("evaluateCounterDelta returns PASS when delta matches expected", () => {
    const result = evaluateCounterDelta("duplicate", 5, 6, 1);
    expect(result.status).toBe("PASS");
    expect(result.observed).toBe("duplicate: 5 → 6 (Δ=1)");
    expect(result.evidence).toContain("incremented by exactly 1");
  });

  it("evaluateCounterDelta returns FAIL when delta differs", () => {
    const result = evaluateCounterDelta("out_of_order", 5, 5, 1);
    expect(result.status).toBe("FAIL");
    expect(result.evidence).toContain("Expected Δ=1, got Δ=0");
  });

  it("evaluateCounterDelta returns FAIL when counter is null", () => {
    const result = evaluateCounterDelta("duplicate", null, 1, 1);
    expect(result.status).toBe("FAIL");
    expect(result.evidence).toContain("Counter unavailable");
  });

  it("evaluateCommandStatus returns PASS when status string matches", () => {
    const result = evaluateCommandStatus(200, "UNKNOWN_VEHICLE", "UNKNOWN_VEHICLE");
    expect(result.status).toBe("PASS");
    expect(result.evidence).toContain("Backend returned expected status: UNKNOWN_VEHICLE");
  });

  it("evaluateCommandStatus returns FAIL when status string differs", () => {
    const result = evaluateCommandStatus(200, "ACCEPTED", "UNKNOWN_VEHICLE");
    expect(result.status).toBe("FAIL");
    expect(result.evidence).toContain('Expected "UNKNOWN_VEHICLE", got "ACCEPTED"');
  });

  it("demoId generates unique non-empty string with prefix", () => {
    const id1 = demoId("TEST");
    const id2 = demoId("TEST");
    expect(id1).toMatch(/^DEMO-TEST-\d+-[a-z0-9]+$/);
    expect(id1).not.toBe(id2);
  });

  it("demoSequence generates high sequence numbers to avoid collision with producer", () => {
    const seq = demoSequence();
    expect(seq).toBeGreaterThanOrEqual(10_000_000);
    expect(seq).toBeLessThan(100_000_000);
  });
});

describe("demoLabClient scenario runners with mock fetch (Phase 10)", () => {
  it("malformed-json runner sends raw body and expects 400", async () => {
    const mockFetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.body).toBe("{bad json here}");
      return new Response(JSON.stringify({ detail: "Invalid JSON" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["malformed-json"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
    expect(result.observed).toBe("HTTP 400");
  });

  it("invalid-speed-type runner sends string speed and expects 400", async () => {
    const mockFetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
      const parsed = JSON.parse(init?.body as string);
      expect(parsed.speed).toBe("fast");
      return new Response(JSON.stringify({ detail: "Speed must be numeric" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["invalid-speed-type"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
  });

  it("negative-speed runner sends negative speed and expects 400", async () => {
    const mockFetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
      const parsed = JSON.parse(init?.body as string);
      expect(parsed.speed).toBe(-5.0);
      return new Response(JSON.stringify({ detail: "Speed cannot be negative" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["negative-speed"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
  });

  it("unknown-vehicle runner checks response.status == UNKNOWN_VEHICLE", async () => {
    const mockFetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
      const parsed = JSON.parse(init?.body as string);
      expect(parsed.vehicle_id).toBe("GHOST_TRUCK_X");
      return new Response(JSON.stringify({ status: "UNKNOWN_VEHICLE", detail: "Unknown" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["unknown-vehicle"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
    expect(result.observed).toContain("UNKNOWN_VEHICLE");
  });

  it("invalid-action runner sends invalid action and expects 400", async () => {
    const mockFetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
      const parsed = JSON.parse(init?.body as string);
      expect(parsed.action).toBe("EXPLODE");
      return new Response(JSON.stringify({ detail: "Invalid action" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["invalid-action"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
  });

  it("duplicate-command runner submits twice and checks second is DUPLICATE", async () => {
    let callCount = 0;
    const mockFetch = async () => {
      callCount++;
      if (callCount === 1) {
        return new Response(JSON.stringify({ status: "ACCEPTED" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ status: "DUPLICATE" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["duplicate-command"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
    expect(result.observed).toContain("Second: DUPLICATE");
  });

  it("oversized-payload runner sends >64KiB and expects 413", async () => {
    const mockFetch = async (_url: RequestInfo | URL, init?: RequestInit) => {
      const len = (init?.body as string).length;
      expect(len).toBeGreaterThan(65536);
      return new Response(JSON.stringify({ detail: "Payload too large" }), {
        status: 413,
        headers: { "Content-Type": "application/json" },
      });
    };

    const runners = createScenarioRunners(mockFetch as unknown as typeof fetch);
    const runner = runners["oversized-payload"];
    expect(runner).toBeDefined();
    const result = await runner!();
    expect(result.status).toBe("PASS");
    expect(result.observed).toBe("HTTP 413");
  });
});
