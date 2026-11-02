// AI contribution: 50% or more AI-generated
/**
 * Where the preview saves runs and the report reads them: always
 * frontend/usability-runs.jsonl (ignored by Git), never a path from the command line.
 */
import { fileURLToPath } from "node:url";

export const RUNS_FILE = fileURLToPath(new URL("../../usability-runs.jsonl", import.meta.url));
