// 与后端交互的 API 封装。开发与生产均使用相对路径（开发期由 Vite 代理到后端）。

export async function getConfig() {
  const r = await fetch('/api/config')
  if (!r.ok) throw new Error('获取配置失败')
  return r.json()
}

export async function getItems() {
  const r = await fetch('/api/items')
  if (!r.ok) throw new Error('获取衣橱失败')
  return r.json()
}

export async function deleteItem(id) {
  const r = await fetch(`/api/items/${id}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('删除失败')
  return r.json()
}

export async function getItem(id) {
  const r = await fetch(`/api/items/${id}`)
  if (!r.ok) throw new Error('获取单品详情失败')
  return r.json()
}

// ---------------- 日历穿搭 outfits ----------------

export async function getOutfits(date) {
  const url = date ? `/api/outfits?date=${encodeURIComponent(date)}` : '/api/outfits'
  const r = await fetch(url)
  if (!r.ok) throw new Error('获取日历穿搭失败')
  return r.json()
}

export async function saveOutfit(date, items, note = '') {
  const r = await fetch('/api/outfits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date, items, note }),
  })
  if (!r.ok) throw new Error('保存穿搭失败')
  return r.json()
}

export async function deleteOutfit(date) {
  const r = await fetch(`/api/outfits/${encodeURIComponent(date)}`, { method: 'DELETE' })
  if (!r.ok) throw new Error('删除穿搭失败')
  return r.json()
}

// 第一步：上传图片，仅做 VL 视觉分析，返回候选单品（不分割、不入库）
export async function analyzePhoto(file) {
  const fd = new FormData()
  fd.append('photos', file)
  const r = await fetch('/api/analyze', { method: 'POST', body: fd })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || '分析失败')
  return data
}

// 第二步：对确认的单品做分割，返回预览图（不入库）
export async function segmentItems(photoUrl, items) {
  const r = await fetch('/api/segment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ photoUrl, items }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || '分割失败')
  return data
}

// 第三步：将确认的单品正式入库
export async function commitItems(items) {
  const r = await fetch('/api/commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || '入库失败')
  return data
}

// ---------------- 用户照片（AI 试穿底图） ----------------

export async function getUserPhoto() {
  const r = await fetch('/api/user/photo')
  if (!r.ok) throw new Error('获取用户照片失败')
  return r.json()
}

export async function uploadUserPhoto(file) {
  const fd = new FormData()
  fd.append('photo', file)
  const r = await fetch('/api/user/photo', { method: 'POST', body: fd })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || '上传失败')
  return data
}

// ---------------- AI 试穿 ----------------

export async function tryOn(itemIds) {
  const r = await fetch('/api/tryon', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ itemIds }),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || '试穿生成失败')
  return data
}

/** 保存试穿记录 */
export async function saveTryOnRecord(itemIds, resultUrl) {
  const r = await fetch('/api/tryon/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ itemIds, resultUrl }),
  })
  let detail = '保存失败'
  try {
    const data = await r.json()
    if (!r.ok) detail = data.detail || detail
    else return data
  } catch {
    if (!r.ok) detail = `服务器错误 (${r.status})`
  }
  throw new Error(detail)
}

/** 获取试穿记录列表 */
export async function getTryOnRecords() {
  const r = await fetch('/api/tryon/records')
  if (!r.ok) throw new Error('获取试穿记录失败')
  return r.json()
}

/** 删除试穿记录 */
export async function deleteTryOnRecord(recordId) {
  const r = await fetch(`/api/tryon/records/${encodeURIComponent(recordId)}`, {
    method: 'DELETE',
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || '删除失败')
  return data
}
