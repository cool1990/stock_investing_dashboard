import { defineConfig } from 'vitest/config';
import { resolve } from 'node:path';

export default defineConfig({
  // GitHub Pages: https://cool1990.github.io/stock_investing_dashboard/
  base: '/stock_investing_dashboard/',
  envPrefix: ['VITE_'],
  root: resolve(import.meta.dirname),
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    port: 43123,
    strictPort: true,
  },
  test: {
    environment: 'node',
  },
});
