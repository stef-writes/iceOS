/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    const upstream = process.env.API_INTERNAL_URL || 'http://api:8000';
    return [
      { source: '/api/:path*', destination: `${upstream}/api/:path*` },
      { source: '/readyz', destination: `${upstream}/readyz` },
    ];
  },
};

module.exports = nextConfig;
