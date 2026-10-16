import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Photos compressées dans le navigateur ; Vercel plafonne de toute façon les requêtes à 4,5 Mo.
  experimental: { serverActions: { bodySizeLimit: "4.5mb" } },
  // Le navigateur appelle /api/backend/* : pas de CORS ni d'URL d'API exposée.
  async rewrites() {
    return [{ source: "/api/backend/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

export default nextConfig;
