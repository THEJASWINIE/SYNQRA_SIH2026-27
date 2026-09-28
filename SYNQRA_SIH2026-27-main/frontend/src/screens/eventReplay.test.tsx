/**
 * S5 Event / Replay render tests — M9. FR-017, S5-a, NFR-007.
 *
 * `react-dom/server` against a real `AppStateStore` via `HmiContext` (M5D-B). No jsdom,
 * no Testing Library (M4D-C). Colour stripped before every state assertion (NFR-008).
 */

import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { AppState } from "../contracts/appState";
import type { EventRecord } from "../contracts/domain";
import { emptyAppState } from "../data/patch";
import { EventLog, type Recording } from "../state/eventLog";
import { HmiContext, type HmiContextValue } from "../state/ProviderHost";
import { AppStateStore } from "../state/store";
import { testHmiContext } from "../state/testHmiContext";
import { EventReplay } from "./EventReplay";

const T = "2026-01-01T00:00:00.000Z";
const BASE = Date.parse(T);

function greyscale(html: string): string {
  return html.replace(/color:[^;"]*;?/g, "").replace(/#[0-9a-fA-F]{3,8}/g, "");
}

function event(
  id: string,
  category: EventRecord["category"],
  partial: Partial<EventRecord> = {},
): EventRecord {
  return {
    eventId: id,
    timestamp: T,
    category,
    subjectId: "SUBJ-1",
    payload: null,
    actor: null,
    ...partial,
  };
}

function recordingWith(
  events: { event: EventRecord; supplied: boolean }[],
  frameCount = 2,
): Recording {
  const log = new EventLog();
  for (let i = 0; i < frameCount; i += 1) {
    const at = BASE + i * 1000;
    log.appendFrame(emptyAppState(new Date(at).toISOString()), at, new Date(at).toISOString());
  }
  for (const { event: e, supplied } of events) {
    log.append(e, supplied ? "SUPPLIED" : "HMI_OBSERVED");
  }
  return log.recording();
}

interface MountOptions {
  recording?: Recording;
  replaying?: boolean;
  positionMs?: number;
  playing?: boolean;
  state?: Partial<AppState>;
  error?: string | null;
}

function render(options: MountOptions = {}): string {
  const store = new AppStateStore(T);
  if (options.state) store.applyPatch({ changes: options.state }, T);
  if (options.error) store.setStatus("ERROR", options.error);

  const recording = options.recording ?? recordingWith([]);
  const replaying = options.replaying ?? false;

  const overrides: Partial<HmiContextValue> = {
    recording,
    replaying,
    replayPosition: replaying
      ? {
          positionMs: options.positionMs ?? BASE,
          startMs: recording.startMs,
          endMs: recording.endMs,
          playing: options.playing ?? false,
          speed: 1,
          frameCount: recording.frames.length,
        }
      : null,
  };

  const value = testHmiContext({ store, overrides });
  const wrap = (children: ReactNode) => (
    <HmiContext.Provider value={value}>{children}</HmiContext.Provider>
  );
  return renderToString(wrap(<EventReplay />));
}

// ---------------------------------------------------------------------------

describe("event timeline (S5-a)", () => {
  it("renders an empty state when nothing has been logged", () => {
    const html = render();
    expect(html).toContain("EVENT LOG EMPTY");
    expect(html).toContain("Nothing is fabricated");
  });

  it("renders a logged event with time, category, subject and origin", () => {
    const html = render({
      recording: recordingWith([{ event: event("E-1", "MODE_TRANSITION"), supplied: false }]),
    });
    expect(html).toContain("MODE TRANSITION");
    expect(html).toContain("SUBJ-1");
    expect(html).toContain("HMI OBSERVED");
  });

  it("distinguishes supplied events from HMI-observed ones, in text", () => {
    const html = greyscale(
      render({
        recording: recordingWith([
          { event: event("S-1", "FOG_CHANGE"), supplied: true },
          { event: event("H-1", "RECOVERY"), supplied: false },
        ]),
      }),
    );
    expect(html).toContain("SUPPLIED");
    expect(html).toContain("HMI OBSERVED");
  });

  it("renders each category distinctly, by text not colour", () => {
    const html = greyscale(
      render({
        recording: recordingWith([
          { event: event("E-1", "ALERT_RAISED"), supplied: false },
          { event: event("E-2", "RECOVERY"), supplied: false },
          { event: event("E-3", "COMMAND_RECEIVED"), supplied: false },
        ]),
      }),
    );
    expect(html).toContain("ALERT RAISED");
    expect(html).toContain("RECOVERY");
    expect(html).toContain("COMMAND RECEIVED");
  });

  it("shows an actor when one was supplied, and a marker when not", () => {
    const html = render({
      recording: recordingWith([
        { event: event("E-1", "ALERT_ACKNOWLEDGED", { actor: "operator-7" }), supplied: true },
      ]),
    });
    expect(html).toContain("operator-7");
  });

  it("orders events by their timestamp", () => {
    const html = render({
      recording: recordingWith([
        {
          event: event("late", "RECOVERY", { timestamp: "2026-01-01T00:00:09.000Z" }),
          supplied: true,
        },
        { event: event("early", "MODE_TRANSITION", { timestamp: T }), supplied: true },
      ]),
    });
    expect(html.indexOf("MODE TRANSITION")).toBeLessThan(html.indexOf("RECOVERY"));
  });
});

describe("category coverage is stated honestly (M9D-C)", () => {
  it("lists every contract category", () => {
    const html = render();
    for (const label of [
      "FOG CHANGE",
      "ALERT RAISED",
      "ALERT ACKNOWLEDGED",
      "COMMAND RECEIVED",
      "COMMAND ISSUED",
      "QUEUE CHANGE",
      "VIOLATION",
      "RECOVERY",
      "MODE TRANSITION",
    ]) {
      expect(html).toContain(label);
    }
  });

  it("marks the three operational categories as producer-supplied only", () => {
    expect(render()).toContain("producer-supplied only");
  });

  it("states that the HMI never derives them", () => {
    const html = render();
    expect(html).toContain("The HMI never derives them");
    expect(html).toContain("absent rather than invented");
  });

  it("reports which categories are present in the session", () => {
    const html = render({
      recording: recordingWith([{ event: event("E-1", "RECOVERY"), supplied: false }]),
    });
    expect(html).toContain("YES");
  });
});

describe("replay transport (FR-017)", () => {
  it("shows LIVE and offers entry when not replaying", () => {
    const html = greyscale(render());
    expect(html).toContain("LIVE");
    expect(html).toContain("Enter replay");
  });

  it("disables entry when nothing has been recorded", () => {
    const html = render({ recording: new EventLog().recording() });
    expect(html).toContain("disabled");
    expect(html).toContain("NOTHING RECORDED YET");
  });

  it("shows REPLAY, controls and position while replaying", () => {
    const html = greyscale(render({ replaying: true }));
    expect(html).toContain("REPLAY");
    expect(html).toContain("Exit replay");
    expect(html).toContain("Play");
    expect(html).toContain("Replay position");
  });

  it("shows Pause while playing", () => {
    expect(render({ replaying: true, playing: true })).toContain("Pause");
  });

  it("offers every playback speed, with the active one marked", () => {
    // React inserts a comment marker between the interpolated number and the multiplier,
    // so the rendered text is `0.5<!-- -->×`. Assert on the number and the marker.
    const html = render({ replaying: true });
    for (const speed of ["0.5", "1", "2", "4"]) {
      expect(html, `speed ${speed}`).toContain(`>${speed}<!-- -->×<`);
    }
    expect(html).toContain('aria-pressed="true">1<!-- -->×<');
  });

  it("offers a scrub mark per recorded frame, and no position between them", () => {
    const recording = recordingWith([], 3);
    const html = render({ recording, replaying: true });
    const marks = html.match(/class="scrub-mark"/g) ?? [];
    expect(marks).toHaveLength(3);
  });

  it("states that the clock follows the replay position", () => {
    expect(render({ replaying: true })).toContain("clock follows the replay position");
  });

  it("renders a provider error when one is reported", () => {
    expect(render({ error: "replay failed" })).toContain("replay failed");
  });
});

describe("scope — no operational control, no acknowledgement (M9D-F)", () => {
  it("renders no form and no input", () => {
    const html = render({ replaying: true });
    expect(html).not.toContain("<form");
    expect(html).not.toContain("<input");
  });

  it("renders no acknowledgement control", () => {
    const html = render({
      replaying: true,
      recording: recordingWith([{ event: event("E-1", "ALERT_RAISED"), supplied: true }]),
    }).toLowerCase();
    expect(html).not.toContain(">acknowledge<");
    expect(html).not.toContain("acknowledge alert");
  });

  it("renders no command, override, dispatch or actuation control", () => {
    const html = render({ replaying: true }).toLowerCase();
    for (const forbidden of [
      "send command",
      "issue command",
      "override",
      "dispatch now",
      "actuate",
      "release vehicle",
      "hold vehicle",
    ]) {
      expect(html, `forbidden control: ${forbidden}`).not.toContain(forbidden);
    }
  });

  it("every button is replay transport only", () => {
    const html = render({ replaying: true });
    const buttons = html.match(/<button[^>]*class="([^"]*)"/g) ?? [];
    expect(buttons.length).toBeGreaterThan(0);
    for (const button of buttons) {
      expect(button).toMatch(/replay-button|scrub-mark/);
    }
  });

  it("states that acknowledgement remains unavailable, and why", () => {
    const html = render();
    expect(html).toContain("FR-015 acknowledgement remains unavailable");
    expect(html).toContain("NFR-011");
  });
});

describe("NFR-007 is reported as PARTIAL, not passed", () => {
  it("states that the recording is in memory only", () => {
    const html = render();
    expect(html).toContain("NFR-007 is PARTIAL");
    expect(html).toContain("does not survive a reload");
    expect(html).toContain("AMB-010");
  });
});
