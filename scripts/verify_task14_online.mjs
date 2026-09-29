// Optional post-deployment browser smoke test. No site writes or proxy changes.
import { chromium } from '../web/node_modules/playwright/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
const [commit, out] = process.argv.slice(2);
if (!commit || !out) throw new Error('Usage: node scripts/verify_task14_online.mjs COMMIT REPORT_DIR');
await mkdir(out, { recursive: true });
const p = process.env.HTTPS_PROXY || process.env.https_proxy;
const proxyUrl = p ? new URL(p) : null;
const browser = await chromium.launch({
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
  ...(proxyUrl ? { proxy: { server: proxyUrl.origin, username: decodeURIComponent(proxyUrl.username), password: decodeURIComponent(proxyUrl.password) } } : {}),
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
const base = 'https://baiixin.github.io/ClothLOOP-Dataset/';
const result = { commit, cases: [], errors };
try {
  await page.goto(base + 'test-initials/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForFunction(() => document.querySelectorAll('.asset-card').length === 14);
  const catalog = await page.evaluate(async () => (await fetch('../generated/catalog.json', { cache: 'no-cache' })).json());
  assert.equal(catalog.commit, commit);
  assert.equal(catalog['test-initials'].length, 14);
  await page.screenshot({ path: out + '/online-list.png', fullPage: true });
  for (const name of ['ct_00004', 'added_06_13', 'dlayers_00756']) {
    await page.goto(base + `test-initials/${name}/`, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForSelector('.viewer[data-state="ready"]', { timeout: 60000 });
    const video = page.locator('video');
    await video.evaluate(async v => { v.muted = true; await v.play(); });
    await page.waitForFunction(() => document.querySelector('video').currentTime > .25, null, { timeout: 60000 });
    await video.evaluate(v => new Promise(resolve => {
      v.pause(); v.addEventListener('seeked', resolve, { once: true }); v.currentTime = v.duration / 2;
    }));
    const stats = await video.evaluate(v => ({ width: v.videoWidth, height: v.videoHeight, time: v.currentTime, duration: v.duration, error: v.error?.message }));
    assert.equal(stats.width, 1080); assert.equal(stats.height, 1080); assert.ok(Math.abs(stats.time - stats.duration / 2) < .1); assert.ok(!stats.error);
    await page.screenshot({ path: out + `/online-${name}.png`, fullPage: true });
    result.cases.push({ name, ...stats });
    console.log(`Online 3D + playback + seek passed: ${name}`);
  }
  assert.deepEqual(errors, []);
  result.passed = true;
} finally {
  await writeFile(out + '/online-browser.json', JSON.stringify(result, null, 2));
  await browser.close();
}
