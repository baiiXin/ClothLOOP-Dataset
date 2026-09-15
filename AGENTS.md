# Dataset and explorer maintenance

- Scientific data lives in ClothTransformer/, ContourCraft/, and D-LAYERS/. Preserve its original numerical values and provenance unless the user explicitly requests a data change.
- Website source lives in web/, portable build tools in scripts/. Never make deployment depend on the neighbouring DATA workspace, uploaded SMPL models, or absolute server paths.
- Root manifest.json validates the curated scientific payload; web/media/manifest.json validates preview assets. Keep modified indexed metadata hashes current. Do not commit generated GLB, web/dist, node_modules, or browser-test output.
- Keep assumed playback FPS distinct from verified and project-defined FPS. Preserve the 10-second short/long boundary.
- Bind every D-LAYERS initial-state garment to the source human from the same sample and state. Apply one shared display transform, never align individual pieces independently. Clothing-related zero collision counts do not imply zero human self-intersections or full-motion validity.
- Build with `cd web && npm ci && npm run build` after installing scripts/requirements-web.txt. Run `npm test` with Playwright Chromium for interface changes. It uses a strict local static server under /ClothLOOP-Dataset/, not SPA fallback.
- Do not use sudo or CUDA2 on the laboratory server. Existing rendering and browser checks use CPU / SwiftShader.
