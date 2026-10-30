// AI contribution: 50% or more AI-generated
/**
 * Prints the time-to-post results table and median from the preview's runs:
 *
 *   node scripts/usability/report.mjs [usability-runs.jsonl]
 *
 * Paste the output into the Results section of docs/usability/time-to-post.md.
 */
import { readFileSync } from "node:fs";

import { markdownReport, parseRuns } from "./runs.mjs";

const file = process.argv[2] ?? "usability-runs.jsonl";
process.stdout.write(markdownReport(parseRuns(readFileSync(file, "utf8"))));
