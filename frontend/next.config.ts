import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        // Keep the browser on the frontend origin. Port 8000 can be occupied
        // by an older local backend process, so the current SAHAYA backend is
        // intentionally isolated on the internal proxy port below.
        destination: "http://127.0.0.1:8001/api/:path*",
      },
    ];
  },
};

export default nextConfig;
