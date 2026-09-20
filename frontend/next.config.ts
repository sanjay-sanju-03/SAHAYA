import type { NextConfig } from "next";

// Server-only value. In Vercel set BACKEND_URL to the deployed Render URL,
// for example https://sahaya-api.onrender.com. Browsers keep using /api,
// which avoids exposing a backend host or relying on cross-origin requests.
const backendUrl = (process.env.BACKEND_URL || "http://127.0.0.1:8002").replace(/\/$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: backendUrl + "/api/:path*",
      },
    ];
  },
};

export default nextConfig;
