/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:4000/api/:path*" },
      { source: "/health", destination: "http://localhost:4000/health" },
      { source: "/mcp/:path*", destination: "http://localhost:4000/mcp/:path*" },
    ];
  },
};

export default nextConfig;