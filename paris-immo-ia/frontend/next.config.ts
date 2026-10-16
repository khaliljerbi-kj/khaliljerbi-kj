import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Jusqu'à 8 photos de 8 Mo envoyées par la Server Action de création d'annonce.
  experimental: { serverActions: { bodySizeLimit: "70mb" } },
  // Le navigateur appelle /api/backend/* : pas de CORS ni d'URL d'API exposée.
  async rewrites() {
    return [{ source: "/api/backend/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
