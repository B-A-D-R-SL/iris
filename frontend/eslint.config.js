// AI contribution: 50% or more AI-generated
import prettier from "eslint-config-prettier";
import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

/** Tests may render the whole app and fake any layer, so the rules below skip them. */
const TESTS = ["src/**/*.test.{ts,tsx}", "src/test/**"];

/**
 * Layers, top to bottom (docs/guides/design-system.md, "Layers"): a layer imports
 * only from the layers below it, never upward.
 */
const LAYERS = ["app", "areas", "features", "shared"];

function layerRule(layer) {
  const above = LAYERS.slice(0, LAYERS.indexOf(layer));
  const upward = String.raw`^(\.\.?/)+(.*/)?(${above.join("|")})(/|$)`;
  const message = `${layer}/ may only import from the layers below it (${LAYERS.join(" > ")}).`;
  return {
    files: [`src/${layer}/**/*.{ts,tsx}`],
    ignores: TESTS,
    rules: {
      "no-restricted-imports": [
        "error",
        { patterns: [{ regex: upward, caseSensitive: true, message }] },
      ],
      // no-restricted-imports skips import(), such as React.lazy(() => import("…")): same
      // pattern on its source. A selector regex cannot hold "/", so it is written \x2F.
      "no-restricted-syntax": [
        "error",
        {
          selector: `ImportExpression[source.value=/${upward.replaceAll("/", String.raw`\x2F`)}/]`,
          message,
        },
      ],
    },
  };
}

/**
 * Functions still over the size limits, held at today's size so they cannot grow.
 * The pull request that splits a file removes its line (design-system.md, "Size").
 */
const OVER_THE_LIMIT = {
  // FIX-06 (#632)
  "src/features/categories/CategoriesPage.tsx": { lines: 225 },
  // FIX-12 (#638)
  "src/areas/store/components/CategoryPicker.tsx": { lines: 97 },
  "src/areas/store/pages/NewListing.tsx": { lines: 244 },
  "src/shared/forms/FileUpload.tsx": { lines: 90 },
  "src/shared/forms/IntegerField.tsx": { lines: 57 },
  "src/shared/forms/TextField.tsx": { lines: 55 },
  // FIX-14 (#640)
  "src/shared/auth/SignOutButton.tsx": { lines: 51 },
  // No issue yet: listed in the FIX-13 pull request.
  "src/areas/household/pages/ListingDetail.tsx": { lines: 70 },
  "src/areas/public/pages/PartnerApply.tsx": { lines: 329 },
  "src/areas/staff/pages/PartnerApplications.tsx": { lines: 275, complexity: 22 },
  "src/areas/staff/pages/WalkIn/HolderStep.tsx": { lines: 71 },
  "src/areas/staff/pages/WalkIn/MembersStep.tsx": { lines: 87 },
  "src/areas/staff/pages/WalkIn/ReviewStep.tsx": { lines: 57 },
  "src/areas/staff/pages/WalkIn/WalkIn.tsx": { lines: 177, complexity: 18 },
  "src/features/categories/CategoryDialog.tsx": { lines: 111 },
};

function sizeRules({ lines = 50, complexity = 15 } = {}) {
  return {
    "max-lines-per-function": ["error", { max: lines }],
    complexity: ["error", complexity],
  };
}

export default defineConfig([
  globalIgnores(["coverage", "dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  ...LAYERS.slice(1).map(layerRule),
  // Rubric 3.2: 50 lines per function and complexity 15 (FIX-13), tests excluded.
  { files: ["src/**/*.{ts,tsx}"], ignores: TESTS, rules: sizeRules() },
  ...Object.entries(OVER_THE_LIMIT).map(([file, limits]) => ({
    files: [file],
    rules: sizeRules(limits),
  })),
]);
