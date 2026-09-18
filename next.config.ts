import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [],
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  experimental: {
    serverActions: {
      bodySizeLimit: "25mb",
    },
    proxyClientMaxBodySize: "25mb",
  },
};

export default nextConfig;
