// AI Wardrobe 前端逻辑
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

let ALL_ITEMS = [];
let CURRENT = null; // 当前打开详情的单品

// 四大类中文名
const CATEGORY_LABELS = { Top: '上装', Bottom: '下装', Shoes: '鞋', Bag: '包' };
const catLabel = (c) => CATEGORY_LABELS[c] || c;

const COLOR_HEX = {
  '白色': '#ffffff', '黑色': '#111111', '蓝色': '#3b6fb6', '米色': '#d8c5a0',
  '红色': '#c0392b', '绿色': '#2e7d4f', '灰色': '#9aa0a6',
  '粉色': '#e89ab0', '棕色': '#8a5a2b', '黄色': '#e0b73a', '紫色': '#7d4fa0',
  '多色': '#bbbbbb', '未知': '#cccccc',
};

function colorHex(c) {
  return COLOR_HEX[c] || (c && c.startsWith('#') ? c : '#cccccc');
}

async function loadConfig() {
  try {
    const r = await fetch('/api/config');
    const c = await r.json();
    const badge = $('#modeBadge');
    if (c.demoMode) {
      badge.textContent = 'DEMO 模式（未接入 Qwen）';
      badge.className = 'badge badge-demo';
    } else {
      badge.textContent = `LIVE · VL ${c.visionModel} + IMG ${c.imageModel}`;
      badge.className = 'badge badge-live';
    }
  } catch {}
}

async function loadItems() {
  const r = await fetch('/api/items');
  ALL_ITEMS = await r.json();
  renderStats();
  populateFilters();
  renderGallery();
}

function renderStats() {
  const s = $('#stats');
  if (ALL_ITEMS.length === 0) { s.classList.add('hidden'); return; }
  s.classList.remove('hidden');
  const cats = {};
  ALL_ITEMS.forEach((i) => (cats[i.category] = (cats[i.category] || 0) + 1));
  const chips = [`<div class="stat-chip"><b>${ALL_ITEMS.length}</b><span>单品总数</span></div>`];
  Object.entries(cats).forEach(([k, v]) =>
    chips.push(`<div class="stat-chip"><b>${v}</b><span>${catLabel(k)}</span></div>`)
  );
  s.innerHTML = chips.join('');
}

function uniq(arr) {
  return ['', ...Array.from(new Set(arr)).filter(Boolean).sort()];
}

function populateFilters() {
  const f = $('#filters');
  f.classList.toggle('hidden', ALL_ITEMS.length === 0);
  const setOpts = (el, vals, allLabel) => {
    el.innerHTML =
      `<option value="">${allLabel}</option>` +
      vals.filter(Boolean).map((v) => {
        const value = typeof v === 'object' ? v.v : v;
        const label = typeof v === 'object' ? v.label : v;
        return `<option value="${value}">${label}</option>`;
      }).join('');
  };
  setOpts(
    $('#fCategory'),
    uniq(ALL_ITEMS.map((i) => i.category)).map((v) => (v ? { v, label: catLabel(v) } : v)),
    '全部类别'
  );
  setOpts($('#fColor'), uniq(ALL_ITEMS.map((i) => i.color)), '全部颜色');
  setOpts($('#fSeason'), uniq(ALL_ITEMS.map((i) => i.season)), '全部季节');
  setOpts($('#fStyle'), uniq(ALL_ITEMS.map((i) => i.style)), '全部风格');
}

function getFiltered() {
  const q = $('#search').value.trim().toLowerCase();
  const c = $('#fCategory').value;
  const col = $('#fColor').value;
  const sea = $('#fSeason').value;
  const sty = $('#fStyle').value;
  return ALL_ITEMS.filter((i) => {
    if (c && i.category !== c) return false;
    if (col && i.color !== col) return false;
    if (sea && i.season !== sea) return false;
    if (sty && i.style !== sty) return false;
    if (q) {
      const hay = `${i.color} ${i.style} ${i.brand} ${i.material} ${i.pattern} ${i.category} ${catLabel(i.category)}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderGallery() {
  const g = $('#gallery');
  const list = getFiltered();
  $('#empty').classList.toggle('hidden', ALL_ITEMS.length !== 0);
  $('#wardrobeHead').classList.toggle('hidden', ALL_ITEMS.length === 0);
  $('#countHint').textContent =
    list.length === ALL_ITEMS.length
      ? `共 ${ALL_ITEMS.length} 件单品`
      : `显示 ${list.length} / ${ALL_ITEMS.length} 件`;
  if (list.length === 0) { g.innerHTML = ''; return; }
  g.innerHTML = list
    .map(
      (i) => `
      <div class="item-card" data-id="${i.id}">
        <div class="item-img">
          <span class="cat-badge">${catLabel(i.category)}</span>
          <img src="${i.imageUrl}" alt="${catLabel(i.category)}" loading="lazy" />
        </div>
        <div class="item-meta">
          <div class="row1"><span class="color-dot" style="background:${colorHex(i.color)}"></span>${i.color}</div>
          <div class="row2">${i.style} · ${i.material} · ${i.brand === 'Unknown' ? '—' : i.brand}</div>
        </div>
      </div>`
    )
    .join('');
  $$('.item-card').forEach((el) =>
    el.addEventListener('click', () => openModal(el.dataset.id))
  );
}

function openModal(id) {
  const i = ALL_ITEMS.find((x) => x.id === id);
  if (!i) return;
  CURRENT = i;
  $('#modalImg').innerHTML = `<img src="${i.imageUrl}" alt="" />`;
  $('#modalTitle').textContent = `${catLabel(i.category)} · ${i.color}`;
  const tags = [
    ['类别', catLabel(i.category)], ['颜色', i.color], ['季节', i.season], ['材质', i.material],
    ['风格', i.style], ['版型', i.fit], ['图案', i.pattern],
    ['品牌', i.brand === 'Unknown' ? '未知' : i.brand], ['Logo', i.hasLogo ? '有' : '无'],
    ['分割方式', i.segmentMethod === 'qwen-image' ? 'Qwen 图像模型（原图分割）' : i.segmentMethod === 'crop-fallback' ? '裁剪（降级）' : '原图（未分割）'],
  ];
  $('#modalTags').innerHTML = tags
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`)
    .join('');
  $('#modalSource').src = i.sourcePhoto;
  $('#modal').classList.remove('hidden');
}

function closeModal() {
  $('#modal').classList.add('hidden');
  CURRENT = null;
}

async function deleteCurrent() {
  if (!CURRENT) return;
  if (!confirm('确定删除该单品？')) return;
  await fetch(`/api/items/${CURRENT.id}`, { method: 'DELETE' });
  closeModal();
  await loadItems();
}

// 上传
function setupUpload() {
  const dz = $('#dropzone');
  const input = $('#fileInput');
  dz.addEventListener('click', () => input.click());
  input.addEventListener('change', () => { if (input.files.length) upload(input.files); });
  ['dragover', 'dragenter'].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('drag'); })
  );
  ['dragleave', 'drop'].forEach((ev) =>
    dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('drag'); })
  );
  dz.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files && files.length) upload(files);
  });
}

async function upload(files) {
  const fd = new FormData();
  Array.from(files).forEach((f) => fd.append('photos', f));
  const prog = $('#progress');
  prog.classList.remove('hidden');
  $('#progressFill').style.width = '20%';
  $('#progressText').textContent = `正在分析 ${files.length} 张照片…`;
  try {
    const r = await fetch('/api/process', { method: 'POST', body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || '处理失败');
    $('#progressFill').style.width = '100%';
    const total = data.result.reduce((s, p) => s + p.items.length, 0);
    $('#progressText').textContent = `完成！本次新增 ${total} 件单品 ✅`;
    await loadItems();
    setTimeout(() => prog.classList.add('hidden'), 2500);
  } catch (e) {
    $('#progressText').textContent = '出错：' + e.message;
  }
}

// 事件
['input', 'change'].forEach((ev) =>
  ['#search', '#fCategory', '#fColor', '#fSeason', '#fStyle'].forEach((s) =>
    $(s).addEventListener(ev, renderGallery)
  )
);
$('#resetFilters').addEventListener('click', () => {
  $('#search').value = '';
  ['#fCategory', '#fColor', '#fSeason', '#fStyle'].forEach((s) => ($(s).value = ''));
  renderGallery();
});
$$('[data-close]').forEach((el) => el.addEventListener('click', closeModal));
$('#modalDelete').addEventListener('click', deleteCurrent);

// 启动
loadConfig();
setupUpload();
loadItems();
