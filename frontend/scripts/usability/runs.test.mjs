// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import {
  createRunRecorder,
  describeRun,
  markdownReport,
  median,
  parseRuns,
  participantFrom,
  scenarioDifferences,
  summarize,
} from "./runs.mjs";

const FORM = "http://127.0.0.1:5173/store/listings/new";
// Thursday 12 November 2026, 09:00 local time.
const OPENED = new Date(2026, 10, 12, 9, 0).getTime();
const CORRECT = { category: "bakery", quantity: 5, best_before: "2026-11-13" };

/** A finished run for participant `code`, `seconds` long. */
function run(recorder, code, seconds, listing = CORRECT) {
  recorder.formOpened(code, OPENED);
  return recorder.published(code, OPENED + seconds * 1000, listing);
}

describe("participantFrom", () => {
  it("reads the participant code from the page address", () => {
    expect(participantFrom(`${FORM}?participant=P2`)).toBe("P2");
    expect(participantFrom(`${FORM}?participant= p3 `)).toBe("P3");
  });

  it("treats anything else as practice", () => {
    expect(participantFrom(undefined)).toBe("practice");
    expect(participantFrom(FORM)).toBe("practice");
    expect(participantFrom(`${FORM}?participant=Camille`)).toBe("practice");
    expect(participantFrom("not a url")).toBe("practice");
  });
});

describe("scenarioDifferences", () => {
  it("accepts the scenario: 5 bakery items, best before the next day", () => {
    expect(scenarioDifferences(CORRECT, new Date(OPENED))).toEqual([]);
    expect(scenarioDifferences({ ...CORRECT, quantity: "5" }, new Date(OPENED))).toEqual([]);
  });

  it("lists what differs", () => {
    expect(scenarioDifferences({ category: "dry_goods", quantity: 1 }, new Date(OPENED))).toEqual([
      "category dry_goods",
      "quantity 1",
      "best before missing",
    ]);
  });
});

describe("createRunRecorder", () => {
  it("times a run from the form's first load to the accepted post", () => {
    const recorder = createRunRecorder();
    expect(recorder.formOpened("P1", OPENED)).toBe(true);
    // A refetch does not restart the clock.
    expect(recorder.formOpened("P1", OPENED + 20_000)).toBe(false);
    expect(recorder.published("P1", OPENED + 42_349, CORRECT)).toEqual({
      run: 1,
      participant: "P1",
      attempt: 1,
      openedAt: new Date(OPENED).toISOString(),
      publishedAt: new Date(OPENED + 42_349).toISOString(),
      seconds: 42.3,
      differences: [],
    });
  });

  it("keeps each participant's clock separate and counts their attempts", () => {
    const recorder = createRunRecorder();
    recorder.formOpened("P1", OPENED);
    recorder.formOpened("P2", OPENED + 5_000);
    expect(recorder.published("P2", OPENED + 35_000, CORRECT)).toMatchObject({
      participant: "P2",
      seconds: 30,
    });
    expect(recorder.published("P1", OPENED + 50_000, CORRECT)).toMatchObject({
      participant: "P1",
      seconds: 50,
    });
    expect(run(recorder, "P1", 20)).toMatchObject({ run: 3, attempt: 2 });
  });

  it("restores participant attempts and run numbers from saved history", () => {
    const original = createRunRecorder();
    const saved = [run(original, "P1", 48), run(original, "P2", 75), run(original, "P1", 20)];
    const restored = createRunRecorder(parseRuns(saved.map((r) => JSON.stringify(r)).join("\n")));
    expect(run(restored, "P1", 15)).toMatchObject({ run: 4, participant: "P1", attempt: 3 });
    expect(run(restored, "P2", 25)).toMatchObject({ run: 5, participant: "P2", attempt: 2 });
    expect(run(restored, "P3", 50)).toMatchObject({ run: 6, participant: "P3", attempt: 1 });
  });

  it("ignores a post whose form never loaded", () => {
    const recorder = createRunRecorder();
    expect(recorder.published("P1", OPENED, CORRECT)).toBeNull();
    run(recorder, "P1", 30);
    // After a post, the next run waits for the next load.
    expect(recorder.published("P1", OPENED + 60_000, CORRECT)).toBeNull();
  });

  it("restarts the clock when the page is reloaded, not when the form refetches", () => {
    const recorder = createRunRecorder();
    expect(recorder.pageLoaded("P1")).toBe(false); // First load: no clock to drop.
    recorder.formOpened("P1", OPENED);
    recorder.formOpened("P1", OPENED + 10_000); // The tab came back into view.
    expect(recorder.pageLoaded("P1")).toBe(true); // F5 a minute later.
    recorder.formOpened("P1", OPENED + 60_000);
    expect(recorder.published("P1", OPENED + 95_000, CORRECT)).toMatchObject({ seconds: 35 });
  });
});

describe("median and summary", () => {
  it("counts a participant once when old saved sessions contain duplicate first attempts", () => {
    const first = run(createRunRecorder(), "P1", 48);
    const duplicate = run(createRunRecorder(), "P1", 10);
    const second = run(createRunRecorder(), "P2", 60);
    expect(summarize([first, duplicate, second])).toMatchObject({
      counted: [first, second],
      median: 54,
      met: true,
    });
    expect(markdownReport([first, duplicate, second])).toContain("| P1 | 1 | 10.0 | Yes | No |");
  });

  it("takes the middle value, or the mean of the two middle values", () => {
    expect(median([])).toBeNull();
    expect(median([70, 40, 50])).toBe(50);
    expect(median([40, 50, 55, 90])).toBe(52.5);
  });

  it("counts only the first attempt of each participant, never practice", () => {
    const recorder = createRunRecorder();
    const runs = [
      run(recorder, "practice", 120),
      run(recorder, "P1", 48),
      run(recorder, "P2", 75),
      run(recorder, "P2", 30),
      run(recorder, "P3", 52),
    ];
    const summary = summarize(runs);
    expect(summary.counted.map((r) => r.seconds)).toEqual([48, 75, 52]);
    expect(summary).toMatchObject({ median: 52, met: true });
    expect(summarize([run(createRunRecorder(), "P1", 61)])).toMatchObject({ met: false });
  });
});

describe("reports", () => {
  it("reads the saved JSON lines back", () => {
    const recorder = createRunRecorder();
    const saved = [run(recorder, "P1", 48), run(recorder, "P2", 75)];
    const text = saved.map((r) => JSON.stringify(r)).join("\r\n") + "\r\n";
    expect(parseRuns(text)).toEqual(saved);
  });

  it("describes a run for the console", () => {
    const recorder = createRunRecorder();
    expect(describeRun(run(recorder, "P1", 48))).toBe(
      "Run 1 · P1 (attempt 1) · 48 s · matches the scenario",
    );
    expect(describeRun(run(recorder, "P2", 51, { ...CORRECT, quantity: 4 }))).toBe(
      "Run 2 · P2 (attempt 1) · 51 s · differs: quantity 4",
    );
  });

  it("prints the table and the median for the document", () => {
    const recorder = createRunRecorder();
    const runs = [
      run(recorder, "practice", 90),
      run(recorder, "P1", 48),
      run(recorder, "P2", 75, { ...CORRECT, best_before: null }),
      run(recorder, "P3", 52),
    ];
    expect(markdownReport(runs)).toBe(
      [
        "| Participant | Attempt | Time to post (s) | Matches the scenario | Counted |",
        "| --- | --- | --- | --- | --- |",
        "| practice | 1 | 90.0 | Yes | No |",
        "| P1 | 1 | 48.0 | Yes | Yes |",
        "| P2 | 1 | 75.0 | No (best before missing) | Yes |",
        "| P3 | 1 | 52.0 | Yes | Yes |",
        "",
        "Median of P1, P2, P3: **52.0 s** (target 60 s: met).",
        "",
      ].join("\n"),
    );
    expect(markdownReport([])).toContain("No participant run yet.");
  });
});
