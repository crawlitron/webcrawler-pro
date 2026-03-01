/** @type {import("next").NextConfig} */
const nextConfig = {
  output: "standalone",
  // NEXT_PUBLIC_API_URL should be empty string for production (Nginx handles /api/ routing)
  // or http://localhost:8000 for local development without Docker
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "",
  },
};

module.exports = nextConfig;
