/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // @wellbe/ui and @wellbe/api-client are shipped as TS source, so Next must transpile them.
  transpilePackages: ["@wellbe/ui", "@wellbe/api-client"],
  // Emit a self-contained server bundle so the container image stays small and
  // does not need the full monorepo node_modules at runtime.
  output: "standalone",
};

export default nextConfig;
