/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // @wellbe/ui and @wellbe/api-client are shipped as TS source, so Next must transpile them.
  transpilePackages: ["@wellbe/ui", "@wellbe/api-client"],
};

export default nextConfig;
