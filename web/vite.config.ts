import { createReadStream, existsSync } from 'node:fs';
import { join } from 'node:path';
import { defineConfig, type Plugin } from 'vitest/config';
import { resolve } from 'node:path';

function serveRepoData(): Plugin {
  const dataRoot = resolve(import.meta.dirname, '../data');
  return {
    name: 'serve-repo-data',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = (req.url ?? '').split('?')[0];
        const marker = '/data/';
        const i = url.indexOf(marker);
        if (i < 0) return next();
        const rel = decodeURIComponent(url.slice(i + marker.length));
        if (!rel || rel.includes('..')) return next();
        const file = join(dataRoot, rel);
        if (!existsSync(file)) return next();
        res.setHeader('Content-Type', file.endsWith('.ics') ? 'text/calendar' : 'application/json');
        createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  // GitHub Pages: https://cool1990.github.io/stock_investing_dashboard/
  base: '/stock_investing_dashboard/',
  plugins: [serveRepoData()],
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
