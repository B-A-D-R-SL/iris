// AI contribution: 50% or more AI-generated
/**
 * Time-to-post runs for the US-33 usability check (T-05.33.5,
 * docs/usability/time-to-post.md).
 *
 * The facilitator opens /store/listings/new?participant=P1, so every API call
 * of that page carries "P1" in its Referer header. A participant's run starts
 * when their form first loads its categories and ends when their listing is
 * accepted. Pure functions: the preview API supplies the requests and the clock.
 */

/** What every participant is asked to post (the scenario card in the document). */
export const SCENARIO = { category: "bakery", quantity: 5, bestBeforeDaysAfter: 1 };

/** US-33 acceptance: a median time to post of 60 seconds or less. */
export const TARGET_SECONDS = 60;

const PARTICIPANT_CODE = /^P\d{1,2}$/;

/**
 * "P1" from a Referer such as http://127.0.0.1:5173/store/listings/new?participant=p1.
 * Anything else is a "practice" run, which never counts toward the median.
 */
export function participantFrom(referer) {
  if (!referer) return "practice";
  try {
    const code = (new URL(referer).searchParams.get("participant") ?? "").trim().toUpperCase();
    return PARTICIPANT_CODE.test(code) ? code : "practice";
  } catch {
    return "practice";
  }
}

/** A local calendar date as YYYY-MM-DD. */
function localDate(date) {
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** How a posted listing differs from the scenario; empty when it matches. */
export function scenarioDifferences(listing, openedAt) {
  const differences = [];
  if (listing.category !== SCENARIO.category) {
    differences.push(`category ${listing.category ?? "missing"}`);
  }
  if (Number(listing.quantity) !== SCENARIO.quantity) {
    differences.push(`quantity ${listing.quantity ?? "missing"}`);
  }
  const bestBefore = new Date(openedAt);
  bestBefore.setDate(bestBefore.getDate() + SCENARIO.bestBeforeDaysAfter);
  if (listing.best_before !== localDate(bestBefore)) {
    differences.push(`best before ${listing.best_before ?? "missing"}`);
  }
  return differences;
}

/** Turns form loads and accepted posts (times in milliseconds) into numbered runs. */
export function createRunRecorder(previousRuns = []) {
  const openedAt = new Map();
  const attempts = new Map();
  let total = previousRuns.length;
  for (const run of previousRuns) {
    total = Math.max(total, run.run);
    attempts.set(run.participant, Math.max(attempts.get(run.participant) ?? 0, run.attempt));
  }

  return {
    /**
     * The page was (re)loaded: the app asks who is signed in once per load. Drops the
     * participant's running clock so the form's next load starts a fresh run.
     * Returns true when a running clock was dropped.
     */
    pageLoaded(participant) {
      return openedAt.delete(participant);
    },

    /**
     * The first load after a participant's previous post or page reload starts their
     * run; refetches (the tab coming back into view) do not. Returns true when this
     * load started the clock.
     */
    formOpened(participant, at) {
      if (openedAt.has(participant)) return false;
      openedAt.set(participant, at);
      return true;
    },

    /** Ends the participant's run and returns it, or null if their form never loaded. */
    published(participant, at, listing) {
      const start = openedAt.get(participant);
      if (start === undefined) return null;
      openedAt.delete(participant);
      const attempt = (attempts.get(participant) ?? 0) + 1;
      attempts.set(participant, attempt);
      total += 1;
      return {
        run: total,
        participant,
        attempt,
        openedAt: new Date(start).toISOString(),
        publishedAt: new Date(at).toISOString(),
        seconds: Math.round((at - start) / 100) / 10,
        differences: scenarioDifferences(listing, new Date(start)),
      };
    },
  };
}

export function median(values) {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  const value = sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
  return Math.round(value * 10) / 10;
}

/** The first attempt of each participant (P1, P2…): first use is what the target is about. */
export function countedRuns(runs) {
  const firstAttempts = new Map();
  for (const run of runs) {
    if (
      run.participant !== "practice" &&
      run.attempt === 1 &&
      !firstAttempts.has(run.participant)
    ) {
      firstAttempts.set(run.participant, run);
    }
  }
  return [...firstAttempts.values()].sort(
    (a, b) => Number(a.participant.slice(1)) - Number(b.participant.slice(1)),
  );
}

export function summarize(runs) {
  const counted = countedRuns(runs);
  const value = median(counted.map((run) => run.seconds));
  return { counted, median: value, met: value !== null && value <= TARGET_SECONDS };
}

/** Runs saved as JSON lines by the preview API. */
export function parseRuns(text) {
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "")
    .map((line) => JSON.parse(line));
}

/** One line per run, for the preview API's console. */
export function describeRun(run) {
  const scenario =
    run.differences.length === 0
      ? "matches the scenario"
      : `differs: ${run.differences.join(", ")}`;
  return `Run ${run.run} · ${run.participant} (attempt ${run.attempt}) · ${run.seconds} s · ${scenario}`;
}

/** The results table and median, ready to paste into docs/usability/time-to-post.md. */
export function markdownReport(runs) {
  const { counted, median: value, met } = summarize(runs);
  const counts = new Set(counted);
  const rows = runs.map((run) =>
    [
      run.participant,
      run.attempt,
      run.seconds.toFixed(1),
      run.differences.length === 0 ? "Yes" : `No (${run.differences.join(", ")})`,
      counts.has(run) ? "Yes" : "No",
    ].join(" | "),
  );
  const outcome =
    value === null
      ? "No participant run yet."
      : `Median of ${counted.map((run) => run.participant).join(", ")}: **${value.toFixed(1)} s** ` +
        `(target ${TARGET_SECONDS} s: ${met ? "met" : "not met"}).`;
  return [
    "| Participant | Attempt | Time to post (s) | Matches the scenario | Counted |",
    "| --- | --- | --- | --- | --- |",
    ...rows.map((row) => `| ${row} |`),
    "",
    outcome,
    "",
  ].join("\n");
}
