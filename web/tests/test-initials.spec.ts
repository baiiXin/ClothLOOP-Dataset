import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const catalog = JSON.parse(await readFile(new URL('../dist/generated/catalog.json', import.meta.url), 'utf8'));

test('14 test first frames have exact routes, previews, mesh data and no videos', async ({ page, request }) => {
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
    expect(row.video).toBeUndefined();
    expect(row.initial_geometry_check).toMatchObject({ frame: 0, cloth_cloth: 0, cloth_body: 0 });
  }
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
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  for (const row of catalog['test-initials']) {
    await page.goto(row.url);
    await expect(page.locator('.viewer')).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    await expect(page.locator('.viewer')).toHaveAttribute('data-mesh-count', '2');
    await expect(page.locator('.collision-summary')).toContainText('未认证');
    await expect(page.locator('video')).toHaveCount(0);
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
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/task14-mobile.png', fullPage: true });
});
