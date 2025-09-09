/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  // Enable standalone output for slim Docker runtime image
  output: 'standalone',
  async rewrites() {
    const upstream = process.env.API_INTERNAL_URL || 'http://api:8000';
    return [
      // Proxy only backend REST under /api/v1 to avoid clashing with Next.js /api routes (e.g., auth)
      { source: '/api/v1/:path*', destination: `${upstream}/api/v1/:path*` },
      { source: '/readyz', destination: `${upstream}/readyz` },
    ];
  },
};

module.exports = nextConfig;
