// Generate real HTML routes after Vite. A direct request never needs an SPA rewrite.
import { readFile, writeFile, mkdir, cp } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(root, 'web/dist');
const catalog = JSON.parse(await readFile(path.join(dist, 'generated/catalog.json'), 'utf8'));
const html = await readFile(path.join(dist, 'index.html'), 'utf8');
const routes = ['body/', 'cloth/', 'initials/', ...['body', 'cloth', 'initials'].flatMap(k => catalog[k].map(x => x.url))];
for (const route of routes) {
  const destination = path.join(dist, route);
  await mkdir(destination, { recursive: true });
  await writeFile(path.join(destination, 'index.html'), html);
}
await cp(path.join(root, 'web/media'), path.join(dist, 'media'), { recursive: true });
await writeFile(path.join(dist, '404.html'), html);
await writeFile(path.join(dist, '.nojekyll'), '');
console.log(`Generated ${routes.length + 1} static page routes.`);
