/**
 * M1 frontend smoke tests.
 *
 * Rendered with `react-dom/server` so no DOM environment is needed — the shell renders,
 * and the status tokens carry a non-colour channel as NFR-008 requires.
 */

import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import { CONNECTION_TOKENS, connectionToken } from "./theme/statusTokens";

describe("App shell", () => {
  it("renders without throwing", () => {
    const html = renderToString(<App />);
    expect(html).toContain("FOG-ORCHESTRATOR 2.0");
  });

  it("shows the backend connectivity section", () => {
    const html = renderToString(<App />);
    expect(html).toContain("Backend");
  });
});

describe("status tokens (NFR-008)", () => {
  it("gives every connection state a label and a glyph, not colour alone", () => {
    for (const [state, token] of Object.entries(CONNECTION_TOKENS)) {
      expect(token.label, `${state} label`).not.toBe("");
      expect(token.glyph, `${state} glyph`).not.toBe("");
    }
  });

  it("resolves a token for each state", () => {
    expect(connectionToken("connected").label).toBe("Connected");
    expect(connectionToken("error").label).toBe("Unreachable");
  });
});
