import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile(new URL('../dist/generated/catalog.json', import.meta.url), 'utf8'));

test('14 test cases have exact routes, initial meshes and bounded HD previews', async ({ page, request }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('test-initials/');
  await expect(page.locator('.asset-card')).toHaveCount(14);
  await expect(page.locator('video')).toHaveCount(0);
  await expect(page.locator('.context-note')).toContainText('11.74 MB');
  expect(catalog['test-initials']).toHaveLength(14);
  for (const row of catalog['test-initials']) {
    expect((await request.get(row.url)).status()).toBe(200);
    expect((await request.get(row.thumbnail)).status()).toBe(200);
    expect((await request.get(row.mesh)).status()).toBe(200);
    expect(row.video).toMatch(/media\/libuipc\/.*\/video.mp4/);
    expect(row.simulation.width).toBe(1080);
    expect(row.simulation.height).toBe(1080);
    expect((await request.get(row.simulation.iterations)).status()).toBe(200);
    expect((await request.get(row.simulation.provenance)).status()).toBe(200);
    expect((await request.get(row.simulation.smooth.provenance)).status()).toBe(200);
    const timing = await (await request.get(row.simulation.smooth.timesteps)).json();
    expect(timing.frames).toHaveLength(row.simulation.frames);
    const range = await request.get(row.video, { headers: { Range: 'bytes=0-31' } });
    expect(range.status()).toBe(206);
    expect((await range.body()).length).toBe(32);
    expect(row.initial_geometry_check).toMatchObject({ frame: 0, cloth_cloth: 0, cloth_body: 0 });
  }
  expect(catalog['test-initials'].reduce((n: number, r: any) => n + r.simulation.bytes, 0)).toBeLessThan(100_000_000);
  expect(catalog['test-initials'].reduce((n: number, r: any) => n + r.simulation.bytes + r.simulation.smooth.bytes, 0)).toBeLessThan(120_000_000);
  expect(catalog['test-initials'].reduce((n: number, r: any) => n + r.simulation.frames, 0)).toBe(8081);
  await page.getByLabel('数据来源').selectOption('C-IPC');
  await expect(page.locator('.asset-card')).toHaveCount(2);
  await page.getByRole('button', { name: '重置筛选' }).click();
  await page.getByRole('searchbox').fill('ct_00004');
  await expect(page.locator('.asset-card')).toHaveCount(1);
  await page.locator('[data-select]').check();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出选择 JSON' }).click();
  const result = JSON.parse(await readFile((await (await download).path())!, 'utf8'));
  expect(result.records).toHaveLength(1);
  expect(result.records[0].kind).toBe('test-initials');
  await page.goto('test-initials/');
  for (const img of await page.locator('.asset-card img').all()) {
    await img.scrollIntoViewIfNeeded();
    await expect.poll(() => img.evaluate((e: HTMLImageElement) => e.complete && e.naturalWidth > 0)).toBe(true);
    await img.evaluate((e: HTMLImageElement) => e.decode());
  }
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({ path: 'test-results/task14-list.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('all14 joint first-frame viewers load, hide body/cloth and preserve original coordinates', async ({ page }) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const row of catalog['test-initials']) {
    await page.goto(row.url);
    await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    await expect(page.locator('.viewer')).toHaveAttribute('data-mesh-count', '2');
    await expect(page.locator('.collision-summary')).toContainText('未认证');
    const video = page.locator('video');
    await expect(video).toHaveCount(1);
    await expect(video).toHaveAttribute('preload', 'none');
    await expect(video).toHaveAttribute('data-variant', 'smooth');
    await video.evaluate(async (v: HTMLVideoElement) => { v.muted = true; await v.play(); });
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.currentTime)).toBeGreaterThan(0);
    expect(await video.evaluate((v: HTMLVideoElement) => v.videoWidth)).toBe(1080);
    await video.evaluate((v: HTMLVideoElement) => new Promise<void>(resolve => {
      v.pause(); v.addEventListener('seeked', () => resolve(), { once: true }); v.currentTime = v.duration * .5;
    }));
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => !v.seeking && v.readyState >= 2)).toBe(true);
    expect(await video.evaluate((v: HTMLVideoElement) => Math.abs(v.currentTime - v.duration / 2))).toBeLessThan(.1);
    await expect(page.locator('[data-timestep]')).toContainText('Δt');
    await expect(page.locator('[data-timestep]')).toContainText('ms');
    await page.getByLabel('视频版本', { exact: true }).selectOption('flat');
    await expect(video).toHaveAttribute('data-variant', 'flat');
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.readyState >= 2 && Math.abs(v.currentTime - v.duration / 2) < .1)).toBe(true);
    expect(await video.evaluate((v: HTMLVideoElement) => v.currentSrc)).toContain('/media/libuipc/');
    await video.evaluate(async (v: HTMLVideoElement) => { await v.play(); });
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.currentTime - v.duration / 2)).toBeGreaterThan(.02);
    await video.evaluate((v: HTMLVideoElement) => v.pause());
    await page.getByLabel('视频版本', { exact: true }).selectOption('smooth');
    await expect.poll(() => video.evaluate((v: HTMLVideoElement) => v.readyState >= 2 && v.currentSrc.includes('/media/libuipc-smooth/'))).toBe(true);
    expect(Math.abs(await video.evaluate((v: HTMLVideoElement) => v.duration) - row.simulation.frames / row.simulation.fps)).toBeLessThan(.05);
    const left = (await page.locator('.simulation-pair>section').nth(0).boundingBox())!;
    const right = (await page.locator('.simulation-pair>section').nth(1).boundingBox())!;
    expect(right.x).toBeGreaterThan(left.x + left.width - 1);
    expect(Math.abs(left.y - right.y)).toBeLessThan(1);
    await page.getByLabel('人体', { exact: true }).uncheck();
    await expect(page.locator('[data-parts] input:checked')).toHaveCount(1);
    await page.getByLabel('人体', { exact: true }).check();
    await page.getByLabel('衣服', { exact: true }).uncheck();
    await expect(page.locator('[data-parts] input:checked')).toHaveCount(1);
    await page.getByLabel('衣服', { exact: true }).check();
    if (row.id === 'ct_00004' || row.id === 'added_06_13') {
      await page.screenshot({ path: `test-results/task14-${row.id}.png`, fullPage: true });
    }
  }
  expect(errors).toEqual([]);
});

test('test initial page is reachable from home and works on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('./');
  await page.getByRole('link', { name: '查看测试集初值' }).click();
  await expect(page).toHaveURL(/test-initials\/$/);
  await expect(page.locator('.asset-card')).toHaveCount(14);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto('test-initials/ct_00004/');
  await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
  const left = (await page.locator('.simulation-pair>section').nth(0).boundingBox())!;
  const right = (await page.locator('.simulation-pair>section').nth(1).boundingBox())!;
  expect(right.y).toBeGreaterThan(left.y + left.height - 1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/task14-mobile.png', fullPage: true });
});

test('nonuniform timestep readout matches the exact saved interval on both variants', async ({ page, request }) => {
  test.setTimeout(120000);
  for (const name of ['cc_01_01', 'cc_144_02']) {
    const row = catalog['test-initials'].find((r: any) => r.id === name);
    const data = await (await request.get(row.simulation.smooth.timesteps)).json();
    const t = data.frames.find((r: any) => r.dt_min_s != null && r.dt_max_s - r.dt_min_s > 1e-8);
    expect(t).toBeTruthy();
    await page.goto(row.url);
    await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    const v = page.locator('video');
    await v.evaluate(async (v: HTMLVideoElement) => { v.muted = true; await v.play(); v.pause(); });
    await v.evaluate((v: HTMLVideoElement, seconds: number) => new Promise<void>(resolve => {
      v.addEventListener('seeked', () => resolve(), { once: true }); v.currentTime = seconds;
    }), (t.frame + .2) / row.simulation.fps);
    for (const variant of ['smooth', 'flat']) {
      await page.getByLabel('视频版本', { exact: true }).selectOption(variant);
      await expect.poll(() => v.evaluate((v: HTMLVideoElement) => !v.seeking && v.readyState >= 2)).toBe(true);
      await expect(page.locator('[data-timestep]')).toContainText(`源帧 ${t.frame} ·`);
      await expect(page.locator('[data-timestep]')).toContainText((t.dt_min_s * 1000).toFixed(6));
      await expect(page.locator('[data-timestep]')).toContainText((t.dt_max_s * 1000).toFixed(6));
      await expect(page.locator('[data-timestep]')).toContainText('最小–最大');
    }
  }
});
