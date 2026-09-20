import './style.css';
import type { Catalog, Entry, Section } from './types';

const BASE = import.meta.env.BASE_URL;
const app = document.querySelector<HTMLDivElement>('#app')!;
const esc = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const url = (path = '') => BASE + path;
const num = (n?: number) => n == null ? '未提供' : n.toLocaleString('en-US');
const time = (seconds?: number) => {
  if (seconds == null) return '未提供';
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  return `${Math.floor(seconds / 60)} min ${(seconds % 60).toFixed(1)} s`;
};
const sizes = (bytes: number) => bytes < 1e6 ? `${(bytes / 1000).toFixed(1)} KB` : `${(bytes / 1e6).toFixed(2)} MB`;
const fpsNote = (item: Entry) => item.fps_status === 'assumed_playback' ? '（假定）' : item.fps_status === 'project_defined' ? '（项目设定）' : '';
const splitLabel = (split?: string) => ({ train: '训练集', test: '测试集', unassigned: '未纳入本轮划分' }[split || 'unassigned'] || '未纳入本轮划分');
const labels: Record<Section, string> = { body: '人体动作', cloth: '服装资产', initials: '绑定初始状态' };
const descriptions: Record<Section, string> = {
  body: '查看动作内容、序列长度与参数来源，找到适合仿真的运动。',
  cloth: '浏览服装与套装网格，旋转查看轮廓、结构和三角面。',
  initials: '整套查看人体与服装，保留每个样本的选定姿态和碰撞报告。',
};
let data: Catalog;
let selected: Set<string>;
try { selected = new Set(JSON.parse(localStorage.getItem('clothloop.selection.v1') || '[]')); }
catch { selected = new Set(); }
let currentRows: Entry[] = [];
let cleanupViewer: (() => void) | undefined;
const pathname = decodeURIComponent(location.pathname).replace(/index\.html$/, '');
const route = pathname.startsWith(BASE) ? pathname.slice(BASE.length).replace(/\/$/, '') : '__404';
const section = route.split('/')[0] as Section;

function frame(content: string) {
  app.innerHTML = `<a class="skip-link" href="#content">跳转到内容</a>
    <header class="site-header"><div class="header-inner">
      <a class="brand" href="${url()}"><span class="brand-mark" aria-hidden="true">C</span><span>ClothLOOP<small>DATASET EXPLORER</small></span></a>
      <nav aria-label="主导航"><a href="${url()}" ${!route ? 'aria-current="page"' : ''}>总览</a>
      ${Object.entries(labels).map(([key, label]) => `<a href="${url(key + '/')}" ${section === key ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
      <a class="github-link" href="${data.repository}" target="_blank" rel="noopener">GitHub <span aria-hidden="true">↗</span></a>
    </div></header><main id="content">${content}</main>
    <footer><span><strong>ClothLOOP</strong> · 数据、预览与来源</span><span>${data.summary.motions} 条动作 · ${data.summary.garments} 份服装资产 · ${data.summary.initials} 套初始状态</span>
      <a href="${data.repository}/blob/${data.commit}/README.md" target="_blank" rel="noopener">数据说明 ↗</a></footer>`;
  wireImages();
}

function image(item: Entry, cls = '', eager = false) {
  return item.thumbnail ? `<img class="${cls}" src="${url(item.thumbnail)}" alt="${esc(item.source + ' ' + item.id + ' 预览')}" loading="${eager ? 'eager' : 'lazy'}" decoding="async">` : `<div class="image-placeholder">暂无预览</div>`;
}

function wireImages() {
  app.querySelectorAll<HTMLImageElement>('img').forEach(img => img.addEventListener('error', () => {
    const replacement = document.createElement('div');
    replacement.className = 'image-placeholder'; replacement.textContent = '预览暂不可用'; img.replaceWith(replacement);
  }, { once: true }));
}

function badge(text: unknown, tone = '') { return `<span class="badge ${tone}">${esc(text)}</span>`; }

function home() {
  const summary = data.summary;
  const count = (kind: Section, source: string) => data[kind].filter(x => x.source === source).length;
  const featured = [data.body.find(x => x.source === 'ContourCraft')!,
    data.cloth.find(x => x.source === 'ClothTransformer')!, data.initials.find(x => x.id === '01306') || data.initials[0]];
  frame(`<section class="hero"><div class="eyebrow">CLOTHLOOP / RESEARCH COLLECTION</div>
    <div class="hero-heading"><div><h1>从人体动作，<br>到服装与初始状态。</h1><p>按来源浏览，按动作筛选，走近每一份数据。</p></div>
    <div class="hero-note"><span class="status-dot"></span> 当前整理版本 <strong>${summary.sources.length} 个数据来源</strong><small>ClothTransformer · ContourCraft / HOOD-VTO · D-LAYERS</small></div></div>
    <div class="stats"><div><strong>${summary.motions}</strong><span>人体动作序列</span></div><div><strong>${summary.garments}</strong><span>服装 / 套装资产</span></div><div><strong>${summary.initials}</strong><span>人体—服装初值</span></div><div><strong>${num(summary.frames)}</strong><span>动作总帧数</span></div></div>
    </section>
    <section class="collection-section"><div class="section-heading"><h2>探索数据</h2><span>从三个入口开始</span></div>
    <div class="collection-grid">${(['body', 'cloth', 'initials'] as Section[]).map((key, i) => `<a class="collection-card" href="${url(key + '/')}">
      <div class="collection-image">${image(featured[i], '', true)}<span class="collection-number">0${i + 1}</span></div>
      <div class="collection-copy"><div class="eyebrow">${['BODY MOTION', 'GARMENT ASSETS', 'BOUND INITIAL STATES'][i]}</div><h2>${labels[key]} <span>↗</span></h2><p>${descriptions[key]}</p>
      <div class="collection-tags">${[`${summary.motions} 条序列 · 按 10 秒分组`, `${summary.garments} 份静态网格 · 3D 查看`, `${summary.bound_garments} 件服装 · ${summary.restpose} restpose / ${summary.frame0} frame0`][i]}</div></div></a>`).join('')}</div></section>
    <section class="overview-grid"><div class="panel"><div class="section-heading"><h2>数据来源</h2><span>沿用原始来源关系</span></div>
    <table class="source-table"><thead><tr><th>来源</th><th>动作</th><th>服装 / 初值</th></tr></thead><tbody>
      <tr><td><strong>ClothTransformer</strong><small>SMPL 反求与关节修复</small></td><td>${count('body', 'ClothTransformer')}</td><td>${count('cloth', 'ClothTransformer')} 份服装</td></tr>
      <tr><td><strong>ContourCraft / HOOD-VTO</strong><small>${data.body.filter(x => x.group === 'vto52').length} VTO + ${data.body.filter(x => x.group === 'validation8').length} HOOD validation</small></td><td>${count('body', 'ContourCraft')}</td><td>${count('cloth', 'ContourCraft')} 份服装 / 套装</td></tr>
      <tr><td><strong>D-LAYERS / CMU</strong><small>精选动作与已绑定静态初值</small></td><td>${count('body', 'D-LAYERS')}</td><td>${summary.initials} 套初值 · ${summary.bound_garments} 件服装</td></tr>
    </tbody></table></div>
    <div class="panel notes-panel"><div class="eyebrow">阅读数据前</div><h2>保留差异，明确依据。</h2>
      <p>ClothTransformer 的 ${count('body', 'ClothTransformer')} 条序列为近似反求并修复后的 SMPL 参数。其余动作保留已有参数。</p>
      <p>D-LAYERS 的 ${count('body', 'D-LAYERS')} 条动作按假定的 30 FPS 播放，时长会明确标注。初值报告只描述所选静态状态。</p>
      <div class="note-footer">全部 ${summary.motions} 条动作已有预览 · ${summary.missing_motion_categories} 条动作类别未提供<br>
      <a href="${url('body/?split=train')}">训练集 ${summary.body_splits.train} 条</a> · <a href="${url('body/?split=test')}">测试集 ${summary.body_splits.test} 条</a><br>
      未纳入本轮划分 ${summary.body_splits.unassigned} 条，保留供后续选择。</div>
    </div></section>`);
}

function saveSelection() {
  try { localStorage.setItem('clothloop.selection.v1', JSON.stringify([...selected])); } catch { /* export still works */ }
  app.querySelectorAll('[data-selection-count]').forEach(e => { e.textContent = String(selected.size); });
}

function exportSelection() {
  const all = [...data.body, ...data.cloth, ...data.initials];
  const payload = { schema: 'ClothLOOP.explorer-selection.v1', dataset_commit: data.commit,
    exported_at: new Date().toISOString(), records: all.filter(x => selected.has(x.key)).map(x => ({
      key: x.key, source: x.source, id: x.id, kind: x.kind, state: x.state ?? null, split: x.split ?? null,
      files: x.files.map(f => ({ path: f.path, sha256: f.sha256 })) })) };
  const objectUrl = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = objectUrl; link.download = 'clothloop-selection.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

function selectField(name: string, label: string, options: [string, string][]) {
  return `<label class="filter-label">${label}<select name="${name}" aria-label="${label}"><option value="">全部</option>${options.map(([value, text]) => `<option value="${esc(value)}">${esc(text)}</option>`).join('')}</select></label>`;
}

function card(item: Entry) {
  const details = item.kind === 'body' ? `${num(item.frames)} 帧 <span>·</span> ${item.fps} FPS${fpsNote(item)}`
    : `${num(item.vertices)} 顶点 <span>·</span> ${num(item.triangles)} 三角面`;
  const tag = item.kind === 'body' ? `${item.fps_status === 'assumed_playback' ? '≈ ' : ''}${time(item.duration)}` : item.state_label;
  return `<article class="asset-card"><a class="asset-image" href="${url(item.url)}" tabindex="-1" aria-hidden="true">${image(item)}<span class="image-tag">${esc(tag)}</span>${item.kind === 'body' ? '<span class="play-icon" aria-hidden="true">▶</span>' : '<span class="mesh-tag">3D</span>'}</a>
    <div class="asset-copy"><div class="asset-topline"><span class="source-label">${esc(item.source)}</span><label class="selection-label" title="加入本地选择"><input type="checkbox" data-select="${esc(item.key)}" aria-label="选择 ${esc(item.id)}" ${selected.has(item.key) ? 'checked' : ''}><span>选择</span></label></div>
    <h3><a href="${url(item.url)}">${esc(item.id)}</a></h3><p class="asset-category">${esc(item.category)}</p><div class="asset-facts">${details}</div>
    <div class="asset-status">${item.kind === 'body' ? badge(splitLabel(item.split), item.split === 'train' ? 'green' : '') : ''}${badge(item.kind === 'body' ? item.processing_label : item.kind === 'initials' ? `${item.garment_count} 件服装 · 已绑定人体` : '独立资产', item.kind === 'initials' ? 'green' : '')}</div></div></article>`;
}

function listing(kind: Section) {
  const rows = data[kind];
  const sources = [...new Set(rows.map(x => x.source))].sort();
  const categories = [...new Set(rows.flatMap(x => x.categories || [x.category]))].sort();
  const params = new URLSearchParams(location.search);
  frame(`<section class="page-heading"><div class="eyebrow">COLLECTION / ${kind === 'body' ? 'BODY MOTION' : kind === 'cloth' ? 'GARMENT ASSETS' : 'BOUND INITIAL STATES'}</div>
    <h1>${labels[kind]} <span class="heading-count">${rows.length}</span></h1><p>${descriptions[kind]}</p></section>
    ${kind === 'initials' ? `<div class="context-note">当前 ${rows.length} 套所选状态中，${rows.filter(x => x.collision?.clothing_related_all_zero).length} 套的<strong>服装相关碰撞计数为零</strong>；人体自相交另列，检查来源见详情报告。</div>` : kind === 'body' ? `<div class="context-note">按 <strong>10 秒</strong>划分短 / 长序列。带“≈”的时长基于 D-LAYERS 假定的 30 FPS。ClothTransformer 显示最新关节修复对比预览。</div>` : ''}
    <form class="filters" id="filters" role="search"><label class="search-label">搜索<input name="q" type="search" placeholder="序列 ID、名称、类别或来源" autocomplete="off"></label>
    ${selectField('source', '数据来源', sources.map(x => [x, x]))}
    ${kind === 'body' ? selectField('split', '训练 / 测试划分', [['train', '训练集'], ['test', '测试集'], ['unassigned', '未纳入本轮划分']]) : ''}
    ${selectField('category', '类别', categories.map(x => [x, x]))}
    ${kind === 'body' ? selectField('duration', '序列时长', [['short', '短序列 < 10 s'], ['long', '长序列 ≥ 10 s']]) + selectField('fps', '播放帧率', [['30', '30 FPS'], ['60', '60 FPS']]) + selectField('processing', '处理状态', [['repaired', 'SMPL 反求 / 修复'], ['source', '来源参数']]) : ''}
    ${kind === 'initials' ? selectField('state', '选定姿态', [['restpose', 'restpose · 静止姿态'], ['frame0', 'frame0 · 动作首帧']]) + selectField('layers', '服装件数', [['2', '2 件'], ['3', '3 件']]) : ''}
    ${kind !== 'body' ? '<label class="filter-label">最少顶点<input name="vertices" type="number" min="0" step="1000" placeholder="不限"></label>' : ''}
    <button class="text-button reset-filter" type="reset">重置筛选</button></form>
    <div class="results-toolbar"><p id="result-count" role="status" aria-live="polite"></p><div class="toolbar-actions"><label class="only-selected"><input type="checkbox" id="only-selected">仅看已选</label>
    <select id="sort" aria-label="排序"><option value="id">按 ID 排序</option><option value="${kind === 'body' ? 'duration' : 'vertices'}">${kind === 'body' ? '时长从长到短' : '顶点数从多到少'}</option></select></div></div>
    <div id="cards" class="asset-grid"></div><div id="pagination" class="pagination"></div>
    <div class="selection-bar"><span>已选 <strong data-selection-count>${selected.size}</strong> 项 <small>· 保存在当前浏览器</small></span><div><button id="clear-selection" class="text-button">清空选择</button><button id="export-selection" class="button small">导出选择 JSON ↓</button></div></div>`);
  const form = app.querySelector<HTMLFormElement>('#filters')!;
  for (const element of form.elements) {
    if (element instanceof HTMLInputElement || element instanceof HTMLSelectElement) element.value = params.get(element.name) || '';
  }
  const sort = app.querySelector<HTMLSelectElement>('#sort')!;
  if (['id', 'duration', 'vertices'].includes(params.get('sort') || '')) sort.value = params.get('sort')!;
  const onlySelected = app.querySelector<HTMLInputElement>('#only-selected')!;
  onlySelected.checked = params.get('selected') === '1';
  let page = Math.max(1, Number(params.get('page')) || 1);
  const update = () => {
    const values = new FormData(form);
    const q = String(values.get('q') || '').toLocaleLowerCase().trim();
    currentRows = rows.filter(x => {
      if (q && ![x.id, x.source, x.category, x.description || ''].join(' ').toLocaleLowerCase().includes(q)) return false;
      if (values.get('source') && x.source !== values.get('source')) return false;
      if (values.get('split') && x.split !== values.get('split')) return false;
      if (values.get('category') && !(x.categories || [x.category]).includes(String(values.get('category')))) return false;
      if (values.get('duration') === 'short' && !(x.duration! < 10)) return false;
      if (values.get('duration') === 'long' && !(x.duration! >= 10)) return false;
      if (values.get('fps') && String(x.fps) !== values.get('fps')) return false;
      if (values.get('processing') === 'repaired' && x.processing !== 'joint_plausibility_repair') return false;
      if (values.get('processing') === 'source' && x.processing === 'joint_plausibility_repair') return false;
      if (values.get('state') && x.state !== values.get('state')) return false;
      if (values.get('layers') && String(x.garment_count) !== values.get('layers')) return false;
      if (values.get('vertices') && x.vertices! < Number(values.get('vertices'))) return false;
      return !onlySelected.checked || selected.has(x.key);
    }).sort((a, b) => sort.value === 'duration' ? b.duration! - a.duration! : sort.value === 'vertices' ? b.vertices! - a.vertices! : a.source.localeCompare(b.source) || a.id.localeCompare(b.id, undefined, { numeric: true }));
    const pages = Math.max(1, Math.ceil(currentRows.length / 24));
    page = Math.min(page, pages);
    const query = new URLSearchParams();
    for (const [k, v] of values) if (String(v).trim()) query.set(k, String(v).trim());
    if (sort.value !== 'id') query.set('sort', sort.value);
    if (onlySelected.checked) query.set('selected', '1');
    if (page > 1) query.set('page', String(page));
    history.replaceState(null, '', location.pathname + (query.size ? '?' + query.toString() : ''));
    app.querySelector('#result-count')!.textContent = `符合筛选 ${currentRows.length} / ${rows.length} 项${currentRows.length > 24 ? ` · 第 ${page} / ${pages} 页` : ''}`;
    app.querySelector('#cards')!.innerHTML = currentRows.length ? currentRows.slice((page - 1) * 24, page * 24).map(card).join('') : '<div class="empty-state"><h2>没有符合条件的数据</h2><p>试着减少筛选条件，或重置筛选。</p></div>';
    app.querySelector('#pagination')!.innerHTML = pages > 1 ? `<button class="button secondary" data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>← 上一页</button><span>${page} / ${pages}</span><button class="button secondary" data-page="${page + 1}" ${page === pages ? 'disabled' : ''}>下一页 →</button>` : '';
    app.querySelectorAll<HTMLButtonElement>('[data-page]').forEach(button => button.onclick = () => { page = Number(button.dataset.page); update(); form.scrollIntoView({ block: 'start' }); });
    app.querySelectorAll<HTMLInputElement>('[data-select]').forEach(input => input.onchange = () => {
      input.checked ? selected.add(input.dataset.select!) : selected.delete(input.dataset.select!);
      saveSelection(); if (onlySelected.checked) update();
    });
    wireImages();
  };
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', () => { page = 1; update(); });
  form.addEventListener('reset', () => { setTimeout(() => { page = 1; sort.value = 'id'; onlySelected.checked = false; update(); }, 0); });
  sort.onchange = onlySelected.onchange = () => { page = 1; update(); };
  app.querySelector<HTMLButtonElement>('#clear-selection')!.onclick = () => { selected.clear(); saveSelection(); update(); };
  app.querySelector<HTMLButtonElement>('#export-selection')!.onclick = exportSelection;
  update();
}

function facts(rows: [string, unknown][]) { return `<dl class="facts-list">${rows.map(([key, value]) => `<div><dt>${esc(key)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>`; }

function collisionPanel(item: Entry) {
  const c = item.collision;
  if (!c) return `<div class="panel"><h2>碰撞检查</h2><p class="muted">此独立服装资产没有配套的人体绑定碰撞报告，不能判定为无穿插。</p></div>`;
  return `<div class="panel collision-panel"><div class="section-heading"><h2>所选状态的碰撞报告</h2>${badge(c.clothing_related_all_zero ? '服装相关计数为零' : '存在服装相关碰撞', 'green')}</div>
    <p class="muted">来自上传报告 · ${esc(c.state)} · ${c.recomputed ? '已重新计算' : '未重新计算'}。此结果不代表整个动作过程无穿插。</p>
    <div class="collision-summary"><div><strong>${c.clothing_related_all_zero ? '0' : '非零'}</strong><span>服装相关碰撞</span></div><div><strong>${c.human_self_intersections}</strong><span>人体自相交</span></div><div><strong>未提供</strong><span>最小间距</span></div></div>
    <details><summary>查看各部件对的计数</summary><table class="collision-table"><thead><tr><th>部件对</th><th>碰撞对计数</th></tr></thead><tbody>${Object.entries(c.counts).map(([key, count]) => `<tr><td>${esc(c.mesh_order[key[0]])} × ${esc(c.mesh_order[key[1]])}</td><td>${count}</td></tr>`).join('')}</tbody></table></details></div>`;
}

function viewerMarkup() {
  return `<div class="viewer" data-state="loading"><div class="viewer-stage"><canvas aria-label="可交互的三维网格" tabindex="0"></canvas><div class="viewer-corner">3D VIEW</div></div>
    <div class="viewer-toolbar"><div class="view-buttons">${[['reset', '复位'], ['front', '正面'], ['side', '侧面'], ['back', '背面'], ['top', '顶面']].map(([key, text]) => `<button data-view="${key}" class="text-button">${text}</button>`).join('')}</div><div class="viewer-switches"><label><input type="checkbox" data-wire>线框</label><label><input type="checkbox" data-spin>自动旋转</label></div></div>
    <div class="part-toggles" data-parts></div><p class="viewer-status" data-viewer-status role="status">正在加载三维查看器…</p></div>`;
}

async function detail(item: Entry) {
  document.title = `${item.id} · ${labels[item.kind]} · ClothLOOP`;
  const meta: [string, unknown][] = [['来源', item.source], ['ID', item.id]];
  if (item.kind === 'body') meta.push(['动作类别', item.category], ['帧数', num(item.frames)],
    ['播放帧率', `${item.fps} FPS${fpsNote(item)}`],
    ['序列时长', `${item.fps_status === 'assumed_playback' ? '≈ ' : ''}${time(item.duration)}`],
    ['处理状态', item.processing_label], ['来源分组', item.group || '未指定'], ['本轮划分', splitLabel(item.split)]);
  else meta.push(['类别', item.category], ['姿态', item.state_label], ['顶点数', num(item.vertices)],
    ['三角面数', num(item.triangles)], ['人体绑定', item.body_bound ? '已绑定 · 同样本同状态' : '未绑定'],
    ...(item.garment_count ? [['服装件数', item.garment_count] as [string, unknown]] : []));
  if (item.source_segment) meta.push(['原动作', item.source_segment.source_sequence_id], ['原动作帧号（从0计）', `${item.source_segment.start_inclusive}–${item.source_segment.end_exclusive - 1}`]);
  const media = item.kind === 'body' ? `<div class="video-panel"><video controls playsinline preload="none" poster="${url(item.thumbnail || '')}" aria-label="${esc(item.id)} 动作视频"><source src="${url(item.video || '')}" type="video/mp4"></video><p class="video-error" hidden>视频加载失败，请使用下方链接单独打开。</p><p>${esc(item.preview_note)} <a href="${url(item.video || '')}" target="_blank" rel="noopener">单独打开视频 ↗</a></p></div>` : viewerMarkup();
  frame(`<div class="breadcrumbs"><a href="${url()}">总览</a><span>/</span><a href="${url(item.kind + '/')}">${labels[item.kind]}</a><span>/</span><span>${esc(item.id)}</span></div>
    <section class="detail-heading"><div><div class="eyebrow">${esc(item.source)}</div><h1>${esc(item.id)}</h1><p>${esc(item.description || (item.kind === 'initials' ? item.category : item.category_basis || ''))}</p></div>
    <button class="button secondary" id="detail-select">${selected.has(item.key) ? '✓ 已加入选择' : '+ 加入选择'}</button></section>
    <div class="detail-grid"><div class="detail-main">${media}
    ${item.kind === 'body' ? (item.processing === 'joint_plausibility_repair' ? '<div class="context-note">本序列由原始人体网格反求 SMPL 后进行关节合理性修复，属于近似重建；参数与修复后网格的一致性不等于对原网格的逐点拟合误差。</div>' : '') : collisionPanel(item)}
    ${item.contact ? `<details class="panel contact-panel"><summary>多视角 / 时间采样预览</summary><img src="${url(item.contact)}" loading="lazy" alt="${esc(item.id)} 多视角或时间采样预览"></details>` : ''}
    <details class="panel"><summary>完整元数据与来源记录</summary><pre>${esc(JSON.stringify(item.metadata, null, 2))}</pre></details></div>
    <aside class="detail-sidebar"><section class="panel"><h2>资产信息</h2>${facts(meta)}${item.category_basis ? `<p class="small-note">${esc(item.category_basis)}</p>` : ''}${item.related_url ? `<a class="button secondary" href="${url(item.related_url)}">${item.kind === 'body' ? '查看对应服装初值' : '查看对应人体片段'}</a>` : ''}</section>
    ${item.model ? `<section class="panel"><h2>SMPL 重建信息</h2>${facts([['模型性别', item.model.gender], ['模型文件', item.model.required_model_filename], ['缩放', item.model.scale], ['模型是否随数据提供', '未打包']])}<p class="small-note">坐标沿用来源单位，不能默认视为米。模型选择性别为拟合结果。</p></section>` : ''}
    <section class="panel"><h2>数据文件</h2><p class="small-note">原始精度数据 · 链接固定到本版提交</p><ul class="file-list">${item.files.map(f => `<li><a href="${esc(f.url)}" target="_blank" rel="noopener">${esc(f.path.split('/').slice(-2).join('/'))} ↗</a><div><span>${sizes(f.bytes)}</span><a href="${esc(f.raw_url)}" target="_blank" rel="noopener">原文件 ↓</a></div><details><summary>SHA-256</summary><code>${f.sha256}</code></details></li>`).join('')}</ul></section></aside></div>`);
  app.querySelector<HTMLButtonElement>('#detail-select')!.onclick = event => {
    selected.has(item.key) ? selected.delete(item.key) : selected.add(item.key); saveSelection();
    (event.target as HTMLButtonElement).textContent = selected.has(item.key) ? '✓ 已加入选择' : '+ 加入选择';
  };
  if (item.kind === 'body') {
    const video = app.querySelector('video')!;
    const showError = () => { app.querySelector<HTMLElement>('.video-error')!.hidden = false; };
    video.addEventListener('error', showError);
    video.querySelector('source')!.addEventListener('error', showError);
  } else if (item.mesh) {
    try {
      const { mountViewer } = await import('./viewer');
      cleanupViewer = await mountViewer(app.querySelector<HTMLElement>('.viewer')!, item, url(item.mesh));
    } catch {
      const status = app.querySelector<HTMLElement>('[data-viewer-status]');
      if (status?.textContent === '正在加载三维查看器…') status.textContent = '三维查看器加载失败。请刷新，或查看多视角图片。';
    }
  }
}

async function boot() {
  const response = await fetch(url('generated/catalog.json'));
  if (!response.ok) throw new Error('catalog unavailable');
  data = await response.json() as Catalog;
  if (data.schema !== 'ClothLOOP.explorer.v1') throw new Error('catalog schema mismatch');
  const valid = new Set([...data.body, ...data.cloth, ...data.initials].map(x => x.key));
  selected = new Set([...selected].filter(x => valid.has(x)));
  if (!route) home();
  else if (['body', 'cloth', 'initials'].includes(route)) listing(route as Section);
  else {
    const item = [...data.body, ...data.cloth, ...data.initials].find(x => x.url.replace(/\/$/, '') === route);
    if (item) await detail(item);
    else frame(`<section class="empty-state"><div class="eyebrow">404</div><h1>未找到这份数据</h1><p>该链接可能已经过期，请从总览重新浏览。</p><a class="button" href="${url()}">返回总览</a></section>`);
  }
}

window.addEventListener('pagehide', () => cleanupViewer?.());
window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
boot().catch(() => {
  app.innerHTML = `<section class="empty-state"><h1>数据索引暂时无法加载</h1><p>请检查网络后刷新页面。</p><button class="button" id="retry">重新加载</button><p><a href="https://github.com/baiiXin/ClothLOOP-Dataset">前往 GitHub 查看数据</a></p></section>`;
  app.querySelector('#retry')!.addEventListener('click', () => location.reload());
});
