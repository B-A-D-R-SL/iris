// AI contribution: 50% or more AI-generated
/**
 * Starts the US-33 time-to-post preview (docs/usability/time-to-post.md):
 *
 *   node scripts/usability/preview.mjs [--port 8000] [--out usability-runs.jsonl]
 *
 * Then run `pnpm dev` (Vite sends /api to port 8000) and open
 * http://localhost:5173/store/listings/new?participant=P1 in the browser's phone view.
 */
import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

import { createPreviewApi } from "./preview-api.mjs";
import { describeRun, summarize, TARGET_SECONDS } from "./runs.mjs";

const { values } = parseArgs({
  options: {
    port: { type: "string", default: "8000" },
    out: { type: "string", default: "usability-runs.jsonl" },
  },
});

const python = fileURLToPath(
  new URL(
    process.platform === "win32"
      ? "../../../backend/.venv/Scripts/python.exe"
      : "../../../backend/.venv/bin/python",
    import.meta.url,
  ),
);
const seed = fileURLToPath(
  new URL("../../../backend/modules/categories/data/categories.yaml", import.meta.url),
);

// The real seed list (SET-12), read with the backend's YAML parser.
const categories = JSON.parse(
  execFileSync(
    python,
    [
      "-I",
      "-c",
      "import json, sys, yaml\n" +
        "rows = yaml.safe_load(open(sys.argv[1], encoding='utf-8'))['categories']\n" +
        "keep = ('code', 'name_fr', 'name_en', 'is_food', 'default_value_cents')\n" +
        "print(json.dumps([{k: r[k] for k in keep} for r in rows if r.get('is_active', True)]))",
      seed,
    ],
    { encoding: "utf8" },
  ),
);

const runs = [];
const server = createPreviewApi({
  categories,
  onRestart: (participant) =>
    console.log(`${participant}: page reloaded, the running clock was dropped`),
  onOpen: (participant) => console.log(`${participant}: form loaded, the clock is running`),
  onRun: (run) => {
    runs.push(run);
    appendFileSync(values.out, `${JSON.stringify(run)}\n`);
    console.log(describeRun(run));
    const { counted, median } = summarize(runs);
    if (median !== null) {
      console.log(
        `  Median of ${counted.map((r) => r.participant).join(", ")}: ${median} s ` +
          `(target ${TARGET_SECONDS} s)`,
      );
    }
  },
});

server.on("error", (error) => {
  if (error.code === "EADDRINUSE") {
    console.error(
      `Port ${values.port} is in use (is the Docker backend running?). ` +
        "Stop it, or use --port and start Vite with API_PROXY_TARGET.",
    );
    process.exit(1);
  }
  throw error;
});

server.listen(Number(values.port), "127.0.0.1", () => {
  console.log(
    `Time-to-post preview API on http://127.0.0.1:${values.port} (${categories.length} categories)`,
  );
  console.log(`Runs are saved to ${values.out}. Open, for each participant:`);
  console.log("  http://localhost:5173/store/listings/new?participant=P1");
});
