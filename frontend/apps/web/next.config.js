/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
  // Enable standalone output for slim Docker runtime image
  output: 'standalone',
  async rewrites() {
    return [{ source: '/api/:path*', destination: 'http://localhost:8000/:path*' }];
  },
};

module.exports = nextConfig;
