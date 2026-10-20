// AI contribution: 50% or more AI-generated
// Run with node:test, separately from Vitest.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { appendFile, mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const script = fileURLToPath(new URL("./gen-api.mjs", import.meta.url));

function runGenerator(output, check = false) {
  const result = spawnSync(
    process.execPath,
    [script, "--output", output, ...(check ? ["--check"] : [])],
    { encoding: "utf8" },
  );
  assert.ifError(result.error);
  return result;
}

test("generation is deterministic and drift checks do not rewrite output", async (t) => {
  const directory = await mkdtemp(join(tmpdir(), "iris-api-generation-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const output = join(directory, "generated.d.ts");

  let result = runGenerator(output);
  assert.equal(result.status, 0, result.stderr);
  const first = await readFile(output, "utf8");
  assert.match(first, /health_retrieve/);

  result = runGenerator(output);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(await readFile(output, "utf8"), first);

  result = runGenerator(output, true);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(await readFile(output, "utf8"), first);

  await appendFile(output, "// Simulated drift in a temporary copy.\n");
  const outdated = await readFile(output, "utf8");
  result = runGenerator(output, true);
  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stderr, /missing or outdated/);
  assert.equal(await readFile(output, "utf8"), outdated);

  const missing = join(directory, "missing.d.ts");
  result = runGenerator(missing, true);
  assert.equal(result.status, 1, result.stderr);
  await assert.rejects(stat(missing), { code: "ENOENT" });
});
