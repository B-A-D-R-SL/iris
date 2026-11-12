// AI contribution: 50% or more AI-generated
/**
 * The layer rule and the size limits of eslint.config.js (FIX-13): checked on
 * sample code, so a config change that stops enforcing them fails here.
 */
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

// Tests run from frontend/ (pnpm test, CI), where ESLint finds eslint.config.js.
const eslint = new ESLint();

async function rulesBroken(filePath: string, code: string): Promise<string[]> {
  const [result] = await eslint.lintText(code, { filePath });
  return result.messages.map((message) => message.ruleId ?? "parse error");
}

const LONG = `export function long() {\n${"  console.log(1);\n".repeat(50)}}\n`;

describe("layer rule: app > areas > features > shared, never upward", () => {
  it.each([
    ["src/shared/auth/sample.ts", "../../features/accounts/invitations"],
    ["src/shared/ui/sample.ts", "../../areas/household/listingFormat"],
    ["src/shared/sample.ts", "../app/navigation"],
    ["src/features/listings/sample.ts", "../../areas/household/listingFormat"],
    ["src/features/listings/sample.ts", "../../app/navigation"],
    ["src/areas/store/pages/sample.ts", "../../../app/navigation"],
  ])(
    "refuses %s importing %s",
    async (filePath, source) => {
      const code = `import type * as Above from "${source}";\nexport type Sample = typeof Above;\n`;
      expect(await rulesBroken(filePath, code)).toContain("no-restricted-imports");
    },
    30_000,
  );

  it.each([
    ["src/app/sample.ts", "../areas/household/listingFormat"],
    ["src/areas/store/pages/sample.ts", "../../../features/listings/api"],
    ["src/areas/store/pages/sample.ts", "../../../shared/ui"],
    ["src/features/listings/sample.ts", "../../shared/logger"],
    ["src/features/listings/sample.ts", "../categories/api"],
    ["src/shared/auth/sample.test.ts", "../../app/App"],
  ])(
    "lets %s import %s",
    async (filePath, source) => {
      const code = `import type * as Below from "${source}";\nexport type Sample = typeof Below;\n`;
      expect(await rulesBroken(filePath, code)).not.toContain("no-restricted-imports");
    },
    30_000,
  );
});

describe("size limits: 50 lines per function, complexity 15, tests excluded", () => {
  it("refuses a 52-line function in src/", async () => {
    expect(await rulesBroken("src/shared/sample.ts", LONG)).toContain("max-lines-per-function");
  }, 30_000);

  it("refuses a complexity above 15", async () => {
    const branches = Array.from({ length: 16 }, (_, i) => `  if (n === ${i}) return ${i};`);
    const code = `export function branchy(n: number) {\n${branches.join("\n")}\n  return -1;\n}\n`;
    expect(await rulesBroken("src/shared/sample.ts", code)).toContain("complexity");
  }, 30_000);

  it("leaves tests alone", async () => {
    expect(await rulesBroken("src/shared/sample.test.ts", LONG)).not.toContain(
      "max-lines-per-function",
    );
  }, 30_000);

  it("holds a file on the temporary list at its size today", async () => {
    const longer = `export function long() {\n${"  console.log(1);\n".repeat(330)}}\n`;
    expect(await rulesBroken("src/areas/public/pages/PartnerApply.tsx", longer)).toContain(
      "max-lines-per-function",
    );
  }, 30_000);
});
