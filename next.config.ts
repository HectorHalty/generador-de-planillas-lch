import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [],
  experimental: {
    serverActions: {
      bodySizeLimit: "25mb",
    },
    proxyClientMaxBodySize: "25mb",
  },
};

export default nextConfig;
