import wellbe from "@wellbe/eslint-config";
import parser from "@typescript-eslint/parser";

export default [
  ...wellbe,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { parser },
  },
  { ignores: [".expo/**", "dist/**"] },
];
