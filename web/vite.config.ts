import { defineConfig } from 'vite';

export default defineConfig({
  base: '/ClothLOOP-Dataset/',
  // The ~635 KB Three.js chunk is only requested on a 3D detail page.
  build: { target: 'es2022', sourcemap: false, chunkSizeWarningLimit: 700 },
  server: { host: '127.0.0.1' },
});
