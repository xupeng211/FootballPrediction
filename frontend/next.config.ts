import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 生产环境 standalone 模式配置
  output: 'standalone',

  // API 代理配置
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*', // 代理到后端 FastAPI 服务
      },
    ]
  },

  // 健康检查重定向
  async redirects() {
    return [
      {
        source: '/health',
        destination: '/api/health',
        permanent: false,
      },
    ]
  },

  // 生产环境优化
  swcMinify: true,
  poweredByHeader: false,

  // 图片优化配置
  images: {
    formats: ['image/webp', 'image/avif'],
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },

  // 实验性功能
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },

  // 环境变量
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
};

export default nextConfig;
