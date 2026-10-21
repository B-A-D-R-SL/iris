// AI contribution: 50% or more AI-generated
// Run with node:test, separately from Vitest.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  appendFile,
  chmod,
  link,
  mkdtemp,
  readFile,
  rm,
  stat,
  symlink,
  unlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, join, relative } from "node:path";
import { text } from "node:stream/consumers";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const script = fileURLToPath(new URL("./gen-api.mjs", import.meta.url));
const { values } = parseArgs({ options: { "schema-stdin": { type: "boolean", default: false } } });
const schemaInput = values["schema-stdin"] ? await text(process.stdin) : undefined;

function runGenerator(directory, check = false, options = {}) {
  const result = spawnSync(
    process.execPath,
    [
      script,
      "--temporary-output",
      ...(schemaInput !== undefined ? ["--schema-stdin"] : []),
      ...(check ? ["--check"] : []),
    ],
    { cwd: directory, encoding: "utf8", input: schemaInput, ...options },
  );
  assert.ifError(result.error);
  return result;
}

async function temporaryDirectory(t, prefix = "iris-api-generation-") {
  const directory = await mkdtemp(join(tmpdir(), prefix));
  t.after(() => rm(directory, { recursive: true, force: true }));
  return directory;
}

test("generation is deterministic and drift checks do not rewrite output", async (t) => {
  const directory = await temporaryDirectory(t);
  const output = join(directory, "generated.d.ts");

  let result = runGenerator(directory);
  assert.equal(result.status, 0, result.stderr);
  const first = await readFile(output, "utf8");
  assert.match(first, /health_retrieve/);

  result = runGenerator(directory);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(await readFile(output, "utf8"), first);

  result = runGenerator(directory, true);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(await readFile(output, "utf8"), first);

  await appendFile(output, "// Simulated drift in a temporary copy.\n");
  const outdated = await readFile(output, "utf8");
  result = runGenerator(directory, true);
  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stderr, /missing or outdated/);
  assert.equal(await readFile(output, "utf8"), outdated);

  await unlink(output);
  result = runGenerator(directory, true);
  assert.equal(result.status, 1, result.stderr);
  await assert.rejects(stat(output), { code: "ENOENT" });
});

test("generator does not use executable PATH lookup", async (t) => {
  const directory = await temporaryDirectory(t);
  const result = runGenerator(directory, false, { env: { ...process.env, PATH: "" } });
  assert.equal(result.status, 0, result.stderr);
  assert.match(await readFile(join(directory, "generated.d.ts"), "utf8"), /health_retrieve/);
});

test("CLI output paths and traversal are rejected", async (t) => {
  const directory = await temporaryDirectory(t);
  const outside = await temporaryDirectory(t, "iris-api-outside-");
  const victim = join(outside, "victim.txt");
  await writeFile(victim, "Do not overwrite.\n");

  for (const target of [victim, relative(directory, victim)]) {
    for (const check of [false, true]) {
      const result = spawnSync(
        process.execPath,
        [script, "--output", target, ...(check ? ["--check"] : [])],
        { cwd: directory, encoding: "utf8" },
      );
      assert.ifError(result.error);
      assert.equal(result.status, 1, result.stderr);
      assert.match(result.stderr, /Unknown option '--output'/);
      assert.equal(await readFile(victim, "utf8"), "Do not overwrite.\n");
    }
  }
});

test("temporary output is confined to the permitted directory", async (t) => {
  const outside = await temporaryDirectory(t, "iris-api-outside-");
  const nested = await mkdtemp(join(outside, "iris-api-generation-"));
  const rejectedDirectories = [outside, nested];

  if (typeof process.getuid === "function") {
    const shared = await temporaryDirectory(t);
    await chmod(shared, 0o755);
    rejectedDirectories.push(shared);
  }

  for (const directory of rejectedDirectories) {
    const output = join(directory, "generated.d.ts");
    await writeFile(output, "Do not overwrite.\n");
    for (const check of [false, true]) {
      const result = runGenerator(directory, check);
      assert.equal(result.status, 1, result.stderr);
      assert.match(result.stderr, /Temporary output requires a private iris-api-generation-/);
      assert.equal(await readFile(output, "utf8"), "Do not overwrite.\n");
    }
  }
});

for (const [name, createLink] of [
  ["symbolic", symlink],
  ["hard", link],
]) {
  test(
    `temporary output rejects ${name} links`,
    { skip: name === "symbolic" && process.platform === "win32" },
    async (t) => {
      const outside = await temporaryDirectory(t, "iris-api-outside-");
      const victim = join(outside, "victim.txt");
      await writeFile(victim, "Do not overwrite.\n");

      const directory = await temporaryDirectory(t);
      const output = join(directory, "generated.d.ts");
      await createLink(victim, output);
      for (const check of [false, true]) {
        const result = runGenerator(directory, check);
        assert.equal(result.status, 1, result.stderr);
        assert.match(
          result.stderr,
          /API output must be a regular file without symbolic or hard links/,
        );
        assert.equal(await readFile(victim, "utf8"), "Do not overwrite.\n");
      }
    },
  );
}

test("stdin accepts UTF-8 schemas larger than 1 MiB without Python", async (t) => {
  const directory = await temporaryDirectory(t);
  const description = "Catégorie → français " + "x".repeat(1024 * 1024);
  const schema = JSON.stringify({
    openapi: "3.0.3",
    info: { title: "Fixture", version: "1" },
    paths: {},
    components: { schemas: { Large: { type: "string", description } } },
  });
  const result = spawnSync(process.execPath, [script, "--temporary-output", "--schema-stdin"], {
    cwd: directory,
    encoding: "utf8",
    input: schema,
    env: { ...process.env, PATH: "" },
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stderr);
  const generated = await readFile(join(directory, "generated.d.ts"), "utf8");
  assert.ok(generated.includes(description));
});

test(
  "Python exports UTF-8 schemas larger than 1 MiB",
  { skip: schemaInput !== undefined },
  async (t) => {
    const directory = await temporaryDirectory(t);
    const description = "Catégorie → français " + "x".repeat(1024 * 1024);
    await writeFile(
      join(directory, "large_schema_settings.py"),
      [
        "from iris.settings.local import *",
        `SPECTACULAR_SETTINGS = {**SPECTACULAR_SETTINGS, "APPEND_COMPONENTS": ${JSON.stringify({ schemas: { LargeUTF8Fixture: { type: "string", description } } })}}`,
      ].join("\n"),
    );
    const result = runGenerator(directory, false, {
      env: {
        ...process.env,
        DJANGO_SETTINGS_MODULE: "large_schema_settings",
        PYTHONPATH: [directory, process.env.PYTHONPATH].filter(Boolean).join(delimiter),
        PYTHONUTF8: "0",
        PYTHONIOENCODING: "ascii",
      },
    });
    assert.equal(result.status, 0, result.stderr);
    assert.ok((await readFile(join(directory, "generated.d.ts"), "utf8")).includes(description));
  },
);
