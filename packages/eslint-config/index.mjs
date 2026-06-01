// Shared WellBe ESLint flat config base.
// Apps extend this and add framework-specific configs (e.g. next/core-web-vitals).
import js from "@eslint/js";

/** @type {import("eslint").Linter.Config[]} */
export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: "module",
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-console": ["warn", { allow: ["warn", "error"] }],
    },
  },
  {
    ignores: ["**/dist/**", "**/.next/**", "**/node_modules/**", "**/generated.ts"],
  },
];
