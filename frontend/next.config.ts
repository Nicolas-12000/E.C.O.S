import type { NextConfig } from "next";

const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

const nextConfig: NextConfig = {
  // Configuración para producción
  output: "standalone", // Mejor para despliegue en Vercel
  async rewrites() {
    if (!apiUrl) return [];
    return [
      { source: "/api/:path*", destination: `${apiUrl}/api/:path*` },
      { source: "/ws/:path*", destination: `${apiUrl}/ws/:path*` },
    ];
  },
  eslint: {
    // Solo ejecutar ESLint en producción si es necesario
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Ignorar errores de TypeScript durante el build
    ignoreBuildErrors: true,
  },
  // Configuración de imágenes si es necesario
  images: {
    unoptimized: true, // Para simplificar el despliegue
  },
};

export default nextConfig;
