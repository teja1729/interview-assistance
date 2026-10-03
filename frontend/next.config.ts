import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: { position: "top-right" },
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  async rewrites() {
    // Vercel Services routes /api through the deployment-level rewrite in vercel.json.
    // Keep this proxy for local Next.js development, where the Vercel router is absent.
    if (process.env.VERCEL === "1") return [];
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(self), microphone=(self), geolocation=()",
          },
        ],
      },
    ];
  },
};
export default nextConfig;
