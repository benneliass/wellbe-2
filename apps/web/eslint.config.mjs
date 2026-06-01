import wellbe from "@wellbe/eslint-config";

export default [
  ...wellbe,
  {
    ignores: [".next/**", "next-env.d.ts"],
  },
];
