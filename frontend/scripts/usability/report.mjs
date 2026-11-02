// AI contribution: 50% or more AI-generated
/**
 * Prints the time-to-post results table and median from the preview's runs:
 *
 *   node scripts/usability/report.mjs
 *
 * Paste the output into the Results section of docs/usability/time-to-post.md.
 */
import { readFileSync } from "node:fs";

import { RUNS_FILE } from "./runs-file.mjs";
import { markdownReport, parseRuns } from "./runs.mjs";

process.stdout.write(markdownReport(parseRuns(readFileSync(RUNS_FILE, "utf8"))));
