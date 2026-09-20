import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile(new URL('../dist/generated/catalog.json', import.meta.url), 'utf8'));
const errors = new Map<string, string[]>();
test.beforeEach(async ({ page }, info) => {
  const list: string[] = [];
  errors.set(info.testId, list);
  page.on('pageerror', error => list.push(error.message));
  page.on('console', message => { if (message.type() === 'error') list.push(message.text()); });
});
test.afterEach(async ({}, info) => {
  if (!info.title.includes('fallback')) expect(errors.get(info.testId)).toEqual([]);
});

test('home loads only the catalogue and thumbnails; all real routes exist', async ({ page, request }) => {
  const requests: string[] = [];
  page.on('request', r => requests.push(r.url()));
  await page.goto('./');
  await expect(page.getByRole('heading', { name: '从人体动作， 到服装与初始状态。' })).toBeVisible();
  await expect(page.locator('.collection-card')).toHaveCount(3);
  await expect(page.locator('.stats')).toContainText(catalog.summary.frames.toLocaleString('en-US'));
  expect(requests.filter(x => /\.(glb|mp4)(\?|$)/.test(x))).toEqual([]);
  for (const row of [...catalog.body, ...catalog.cloth, ...catalog.initials]) {
    const response = await request.get(row.url);
    expect(response.status(), row.url).toBe(200);
    const thumb = await request.head(row.thumbnail);
    expect(thumb.status(), row.thumbnail).toBe(200);
  }
  expect((await request.get('does-not-exist/')).status()).toBe(404);
  await page.screenshot({ path: 'test-results/home-desktop.png', fullPage: true });
});

test('body filters, pagination, query persistence, selection and export', async ({ page }) => {
  await page.goto('body/');
  await expect(page.locator('.asset-card')).toHaveCount(24);
  await page.getByRole('button', { name: '下一页' }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByLabel('数据来源').selectOption('D-LAYERS');
  await page.getByLabel('序列时长').selectOption('long');
  const rows = catalog.body.filter((x: any) => x.source === 'D-LAYERS' && x.duration >= 10);
  await expect(page.locator('#result-count')).toContainText(`符合筛选 ${rows.length} / ${catalog.body.length}`);
  await page.reload();
  await expect(page.getByLabel('数据来源')).toHaveValue('D-LAYERS');
  await expect(page.getByLabel('序列时长')).toHaveValue('long');
  await page.locator('[data-select]').first().check();
  await expect(page.locator('[data-selection-count]')).toHaveText('1');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出选择 JSON' }).click();
  const file = await (await download).path();
  const exported = JSON.parse(await readFile(file!, 'utf8'));
  expect(exported.records).toHaveLength(1);
  expect(exported.records[0].source).toBe('D-LAYERS');
  await page.reload();
  await expect(page.locator('[data-selection-count]')).toHaveText('1');
  await page.getByRole('button', { name: '清空选择' }).click();
  await page.getByRole('searchbox').fill('no-such-motion');
  await expect(page.getByRole('heading', { name: '没有符合条件的数据' })).toBeVisible();
  await page.getByRole('button', { name: '重置筛选' }).click();
  await expect(page.locator('.asset-card')).toHaveCount(24);
});

test('video playback on original and latest repaired motion; frame-rate semantics', async ({ page }) => {
  for (const path of ['body/ContourCraft/02_04/', 'body/ClothTransformer/sim_00000/']) {
    await page.goto(path);
    const video = page.locator('video');
    await expect(video).toHaveAttribute('preload', 'none');
    await video.evaluate(async (element: HTMLVideoElement) => { element.muted = true; await element.play(); });
    await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.currentTime)).toBeGreaterThan(0.1);
    await video.evaluate((element: HTMLVideoElement) => element.pause());
  }
  await page.goto('body/ContourCraft/01_01/');
  await expect(page.locator('.facts-list')).toContainText('30 FPS（项目设定）');
  await page.goto('body/D-LAYERS/141_12/');
  await expect(page.locator('.facts-list')).toContainText('30 FPS（假定）');
});

test('GLB viewer renders and controls a bound scene without losing its binding', async ({ page }) => {
  await page.goto('initials/D-LAYERS/01306/');
  await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
  await expect(page.locator('.viewer')).toHaveAttribute('data-mesh-count', '4');
  await expect(page.locator('canvas')).toHaveAttribute('data-rendered', 'true');
  await expect(page.locator('.collision-summary')).toContainText('61');
  const canvas = page.locator('canvas');
  const before = await canvas.screenshot();
  await page.getByRole('button', { name: '侧面', exact: true }).click();
  const after = await canvas.screenshot();
  expect(Buffer.compare(before, after)).not.toBe(0);
  await page.getByLabel('人体', { exact: true }).uncheck();
  await page.getByLabel('jacket', { exact: true }).uncheck();
  await expect(page.locator('[data-parts] input:checked')).toHaveCount(2);
  await page.getByLabel('线框', { exact: true }).check();
  await page.getByLabel('自动旋转', { exact: true }).check();
  await page.getByLabel('自动旋转', { exact: true }).uncheck();
  await page.getByLabel('线框', { exact: true }).uncheck();
  await page.getByLabel('人体', { exact: true }).check();
  await page.getByLabel('jacket', { exact: true }).check();
  await page.getByRole('button', { name: '复位', exact: true }).click();
  const box = await canvas.boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width / 2 + 60, box!.y + box!.height / 2 + 25);
  await page.mouse.up();
  await page.mouse.wheel(0, 90);
  await page.screenshot({ path: 'test-results/initial-detail.png', fullPage: true });
  await page.reload();
  await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
  await page.getByRole('link', { name: '总览', exact: true }).first().click();
  await page.goBack();
  await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
});

test('garment list filtering and independent garment viewer', async ({ page }) => {
  await page.goto('cloth/?source=ClothTransformer');
  await expect(page.locator('.asset-card')).toHaveCount(2);
  await expect(page.locator('#result-count')).toContainText('2 / 59');
  await page.getByRole('link', { name: 'CT-sim_00002', exact: true }).click();
  await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
  await expect(page.locator('.viewer')).toHaveAttribute('data-mesh-count', '1');
  await expect(page.getByText('不能判定为无穿插', { exact: false })).toBeVisible();
});

test('mobile layout and initial-state filters', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ['./', 'body/', 'cloth/', 'initials/']) {
    await page.goto(route);
    await expect(page.locator('header')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.getByLabel('选定姿态').selectOption('restpose');
  await expect(page.locator('#result-count')).toContainText(`${catalog.summary.restpose} / ${catalog.initials.length}`);
  await page.getByLabel('服装件数').selectOption('3');
  const rows = catalog.initials.filter((x: any) => x.state === 'restpose' && x.garment_count === 3);
  await expect(page.locator('#result-count')).toContainText(`${rows.length} / ${catalog.initials.length}`);
  await page.goto('./');
  await page.screenshot({ path: 'test-results/home-mobile.png', fullPage: true });
});

test('fallback states for missing catalogue, image and mesh', async ({ page }) => {
  await page.route('**/generated/catalog.json', route => route.abort());
  await page.goto('./');
  await expect(page.getByRole('heading', { name: '数据索引暂时无法加载' })).toBeVisible();
  await page.unroute('**/generated/catalog.json');
  await page.route('**/*.webp', route => route.abort());
  await page.goto('cloth/?source=ClothTransformer');
  await expect(page.locator('.image-placeholder')).toHaveCount(2);
  await page.unroute('**/*.webp');
  await page.route('**/*.glb', route => route.abort());
  await page.goto('cloth/ClothTransformer/CT-sim_00000/');
  await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'error', { timeout: 30000 });
  await expect(page.locator('[data-viewer-status]')).toContainText('三维网格加载失败');
});

test('approved body splits filter, persist and export without reassigning garments', async ({ page }) => {
  await page.goto('body/?split=train');
  await expect(page.getByLabel('训练 / 测试划分')).toHaveValue('train');
  await expect(page.locator('#result-count')).toContainText('52 / 91');
  await page.getByLabel('训练 / 测试划分').selectOption('test');
  await expect(page.locator('.asset-card')).toHaveCount(12);
  await page.reload();
  await expect(page.getByLabel('训练 / 测试划分')).toHaveValue('test');
  await page.getByLabel('数据来源').selectOption('D-LAYERS');
  await expect(page.locator('.asset-card')).toHaveCount(4);
  await page.getByLabel('选择 00756', { exact: true }).check();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出选择 JSON' }).click();
  const exported = JSON.parse(await readFile((await (await download).path())!, 'utf8'));
  expect(exported.records[0].split).toBe('test');
  await page.goto('body/?split=unassigned');
  await expect(page.locator('#result-count')).toContainText('27 / 91');
  await page.goto('cloth/');
  await expect(page.getByLabel('训练 / 测试划分')).toHaveCount(0);
});

test('sample clips expose exact ranges, play and link to same-sample initial meshes', async ({ page }) => {
  for (const [sid, range, frames] of [['00396', '0–404', '405'], ['00756', '508–772', '265']]) {
    await page.goto(`body/D-LAYERS/${sid}/`);
    await expect(page.locator('.facts-list')).toContainText(range);
    await expect(page.locator('.facts-list')).toContainText(frames);
    await expect(page.locator('.facts-list')).toContainText('测试集');
    const video = page.locator('video');
    await video.evaluate(async (e: HTMLVideoElement) => { e.muted = true; await e.play(); });
    await expect.poll(() => video.evaluate((e: HTMLVideoElement) => e.currentTime)).toBeGreaterThan(0.1);
    await page.getByRole('link', { name: '查看对应服装初值' }).click();
    await expect(page).toHaveURL(new RegExp(`initials/D-LAYERS/${sid}/`));
    await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    await expect(page.locator('.viewer')).toHaveAttribute('data-mesh-count', '3');
    await page.getByRole('link', { name: '查看对应人体片段' }).click();
    await expect(page).toHaveURL(new RegExp(`body/D-LAYERS/${sid}/`));
  }
});
