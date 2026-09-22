(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('case-data').textContent);
  const cases = data.cases;
  const byId = new Map(cases.map(c => [c.id, c]));
  const $ = id => document.getElementById(id);
  const storageKey = 'clothloop-task9-release-20260922-v1';
  const labels = {original: '无穿 · 原方案', substitute: '无穿 · v1.1 新体型', failed: '有穿 · 未通过'};
  const reviewLabels = {pending: '未检查', ok: '已看 · 可接受', issue: '已看 · 需修改'};
  const esc = text => String(text).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  let reviews = {}, filter = 'all', current = null, viewerIds = [], storageAvailable = true;
  let scale = 1, tx = 0, ty = 0, drag = null, lastOpener = null;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    for (const c of cases) {
      const r = saved[c.id];
      if (r && r.sha256 === c.sha256 && Object.hasOwn(reviewLabels, r.state)) {
        reviews[c.id] = {sha256: c.sha256, state: r.state, notes: String(r.notes || '').slice(0, 10000), updated_at: r.updated_at || null};
      }
    }
  } catch (_) { storageAvailable = false; }
  const review = c => reviews[c.id] || {sha256: c.sha256, state: 'pending', notes: '', updated_at: null};
  const badge = c => `<span class="badge ${c.kind}">${labels[c.kind]}</span>`;

  function matches(c) {
    const stateMatches = filter === 'all' || (filter === 'pass' && c.passed) ||
      (filter === 'failed' && !c.passed) || (filter === 'substitute' && c.kind === 'substitute') ||
      (filter === 'pending' && review(c).state === 'pending');
    const query = $('search').value.trim().toLowerCase();
    return stateMatches && `${c.id} ${c.group} ${c.title} ${c.outfit}`.toLowerCase().includes(query);
  }

  function updateProgress() {
    $('review-progress').textContent = `人工检查 ${cases.filter(c => review(c).state !== 'pending').length} / 15`;
    $('storage-status').textContent = storageAvailable ? '备注仅保存在此浏览器，请导出留存。' : '浏览器无法持久保存；当前备注仍在页面内，请导出后再关闭。';
  }

  function renderGrid() {
    const visible = cases.filter(matches);
    $('grid').innerHTML = visible.map(c => {
      const r = review(c);
      return `<article class="card ${c.kind}" data-case="${c.id}">
        <div class="card-top"><span class="card-number">${String(c.number).padStart(2, '0')} / ${esc(c.group)}</span>${badge(c)}</div>
        <button class="preview" data-open="${c.id}" aria-label="放大检查 ${esc(c.title)}">
          <img src="${c.image}" alt="${esc(c.title)} 正背面实际渲染" width="1600" height="900" loading="lazy">
          <span class="zoom-hint">放大检查 ↗</span>
        </button>
        <div class="card-body"><div class="card-title-row"><h2>${esc(c.title)}</h2><span class="review-chip ${r.state}">${reviewLabels[r.state]}</span></div>
          <p class="outfit">${esc(c.outfit)}</p><div class="card-metrics"><span>衣物 CC <b>${c.counts[0]}</b></span><span>人体 CB <b>${c.counts[1]}</b></span><span>内部点 <b>${c.counts[2]}</b></span></div>
          <p class="card-caution">${esc(c.caution)}</p>
        </div></article>`;
    }).join('');
    $('visible-count').textContent = `显示 ${visible.length} / 15 份`;
    $('empty').hidden = visible.length !== 0;
    updateProgress();
  }

  function applyTransform() {
    const vp = $('viewport');
    tx = Math.max(-vp.clientWidth * (scale - 1) / 2, Math.min(vp.clientWidth * (scale - 1) / 2, tx));
    ty = Math.max(-vp.clientHeight * (scale - 1) / 2, Math.min(vp.clientHeight * (scale - 1) / 2, ty));
    $('large-image').style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
    $('zoom').value = Math.round(scale * 100);
    $('zoom-value').textContent = `${Math.round(scale * 100)}%`;
    vp.classList.toggle('zoomed', scale > 1);
  }

  function resetZoom() { scale = 1; tx = 0; ty = 0; applyTransform(); }

  function populate(id) {
    const c = byId.get(id);
    if (!c) return;
    current = c;
    const r = review(c), position = viewerIds.indexOf(id);
    $('viewer-number').textContent = `${String(c.number).padStart(2, '0')} / 15 · ${c.group} · 当前筛选 ${position + 1}/${viewerIds.length}`;
    $('viewer-title').textContent = c.title;
    $('viewer-status').innerHTML = badge(c);
    $('viewer-outfit').textContent = c.outfit;
    $('metrics').className = `metrics ${c.kind}`;
    $('metrics').innerHTML = ['衣物 CC', '人体 CB', '内部点'].map((label, i) => `<div><span>${label}</span><b>${c.counts[i]}</b></div>`).join('');
    $('method').textContent = c.method;
    $('caution').textContent = c.caution;
    $('stretch').textContent = c.stretch ? `相对交付 rest 的主伸长：${c.stretch.minimum.toPrecision(4)} – ${c.stretch.maximum.toPrecision(4)}。参考来源不同，不可简单横向比较。` : '此有穿候选没有统一 rest 伸长验收；不可作为已完成的穿衣初态。';
    $('review-state').value = r.state;
    $('notes').value = r.notes;
    $('save-status').textContent = r.updated_at ? '已载入本浏览器的检查意见' : '备注不会改变已有几何验收状态';
    $('large-image').alt = `${c.title} 正背面实际渲染；${labels[c.kind]}`;
    $('image-error').hidden = true;
    $('large-image').src = c.image;
    $('original-image').href = c.image;
    $('closeup').hidden = !c.closeup;
    if (c.closeup) $('closeup').href = c.closeup;
    $('hash').textContent = c.sha256;
    $('data-links').innerHTML = Object.entries(c.links).map(([label, href]) => `<a target="_blank" rel="noopener" href="${href}">${esc(label)} ↗</a>`).join('');
    $('previous').disabled = position <= 0;
    $('next').disabled = position >= viewerIds.length - 1;
    document.querySelector('.details-panel').scrollTop = 0;
    resetZoom();
  }

  function openViewer(id, opener) {
    viewerIds = cases.filter(matches).map(c => c.id);
    if (!viewerIds.includes(id)) viewerIds = cases.map(c => c.id);
    lastOpener = opener || null;
    populate(id);
    $('viewer').showModal();
    document.body.style.overflow = 'hidden';
    $('close').focus();
  }

  function navigate(direction) {
    if (!current) return;
    const index = viewerIds.indexOf(current.id) + direction;
    if (index >= 0 && index < viewerIds.length) populate(viewerIds[index]);
  }

  function saveReview() {
    if (!current) return;
    reviews[current.id] = {sha256: current.sha256, state: $('review-state').value,
      notes: $('notes').value, updated_at: new Date().toISOString()};
    try { localStorage.setItem(storageKey, JSON.stringify(reviews)); storageAvailable = true; }
    catch (_) { storageAvailable = false; }
    $('save-status').textContent = storageAvailable ? '已保存到本浏览器 · 建议导出留存' : '暂存在页面内 · 请导出留存';
    updateProgress();
  }

  $('grid').addEventListener('click', e => {
    const button = e.target.closest('[data-open]');
    if (button) openViewer(button.dataset.open, button);
  });
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
    filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
    renderGrid();
  }));
  $('search').addEventListener('input', renderGrid);
  $('review-state').addEventListener('change', saveReview);
  $('notes').addEventListener('input', saveReview);
  $('close').addEventListener('click', () => $('viewer').close());
  $('viewer').addEventListener('click', e => { if (e.target === $('viewer')) $('viewer').close(); });
  $('viewer').addEventListener('close', () => {
    const focusId = lastOpener?.dataset.open;
    document.body.style.overflow = '';
    renderGrid();
    const replacement = focusId && document.querySelector(`[data-open="${focusId}"]`);
    if (replacement) replacement.focus({preventScroll: true});
  });
  $('previous').addEventListener('click', () => navigate(-1));
  $('next').addEventListener('click', () => navigate(1));
  $('viewer').addEventListener('keydown', e => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') { e.preventDefault(); navigate(e.key === 'ArrowLeft' ? -1 : 1); }
  });
  $('large-image').addEventListener('error', () => { $('image-error').hidden = false; });
  $('zoom').addEventListener('input', () => { scale = Number($('zoom').value) / 100; applyTransform(); });
  $('reset').addEventListener('click', resetZoom);
  $('viewport').addEventListener('wheel', e => {
    e.preventDefault(); scale = Math.max(1, Math.min(4, scale + (e.deltaY < 0 ? .1 : -.1))); applyTransform();
  }, {passive: false});
  $('viewport').addEventListener('pointerdown', e => {
    if (scale <= 1 || e.button !== 0) return;
    drag = {x: e.clientX - tx, y: e.clientY - ty};
    $('viewport').setPointerCapture(e.pointerId);
    $('viewport').classList.add('dragging');
  });
  $('viewport').addEventListener('pointermove', e => {
    if (drag) { tx = e.clientX - drag.x; ty = e.clientY - drag.y; applyTransform(); }
  });
  for (const event of ['pointerup', 'pointercancel', 'lostpointercapture']) $('viewport').addEventListener(event, () => { drag = null; $('viewport').classList.remove('dragging'); });
  window.addEventListener('resize', applyTransform);
  $('export').addEventListener('click', () => {
    const report = {task: 9, scope: 'User visual inspection only; does not overwrite geometric acceptance.',
      exported_at: new Date().toISOString(), source_page_created_at: data.created_at,
      cases: cases.map(c => ({case: c.id, label: c.title, displayed_variant: c.kind,
        firstframe_sha256: c.sha256, geometry_passed: c.passed,
        strict_cloth_cloth: c.counts[0], strict_cloth_body: c.counts[1], contained_vertices: c.counts[2],
        review: review(c)}))};
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url; link.download = `task9-inspection-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  });
  renderGrid();
})();
