import type { NextConfig } from 'next';
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '/vaca-muerta-pulse';
const config: NextConfig = { output: 'export', basePath, trailingSlash: true, images: { unoptimized: true } };
export default config;
