// 与后端交互的 API 封装。开发与生产均使用相对路径（开发期由 Vite 代理到后端）。

// 统一鉴权 Token（Bearer），所有请求自动带上 Authorization 头。
export const AUTH_TOKEN =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJvcGVuaWQiOiJvTy1wSzVJWERtUXBhMWtqX0FoYVhxeDJvaFJVIiwiaWF0IjoxNzg2MjkyODgwLCJleHAiOjE3ODY4OTc2ODB9.ZtPR97XmK_bJlzSAq_hv1REt65yK2fsTNwC-BV3DT3A'

const AUTH_HEADER = { Authorization: `Bearer ${AUTH_TOKEN}` }

/**
 * 统一请求封装：自动附加 Authorization 头，并解析 JSON 错误。
 * @param {string} url
 * @param {object} opts fetch 选项（headers 会与鉴权头合并）
 */
async function request(url, opts = {}) {
  const headers = { ...AUTH_HEADER, ...(opts.headers || {}) }
  const r = await fetch(url, { ...opts, headers })
  const isJson = (r.headers.get('content-type') || '').includes('application/json')
  const data = isJson ? await r.json() : null
  if (!r.ok) {
    const detail = (data && data.detail) || `请求失败 (${r.status})`
    throw new Error(detail)
  }
  return data
}

export async function getConfig() {
  return request('/api/config')
}

export async function getItems() {
  return request('/api/items')
}

export async function deleteItem(id) {
  return request(`/api/items/${id}`, { method: 'DELETE' })
}

export async function getItem(id) {
  return request(`/api/items/${id}`)
}

// ---------------- 日历穿搭 outfits ----------------

export async function getOutfits(date) {
  const url = date ? `/api/outfits?date=${encodeURIComponent(date)}` : '/api/outfits'
  return request(url)
}

export async function saveOutfit(date, items, note = '') {
  return request('/api/outfits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ date, items, note }),
  })
}

export async function deleteOutfit(date) {
  return request(`/api/outfits/${encodeURIComponent(date)}`, { method: 'DELETE' })
}

// 第一步：上传图片，仅做 VL 视觉分析，返回候选单品（不分割、不入库）
export async function analyzePhoto(file) {
  const fd = new FormData()
  fd.append('photos', file)
  return request('/api/analyze', { method: 'POST', body: fd })
}

// 第二步：对确认的单品做分割，每次只上传一件（返回预览图，不入库）
export async function segmentOne(photoUrl, item) {
  return request('/api/segment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ photoUrl, item }),
  })
}

// 第三步：将确认的单品正式入库
export async function commitItems(items) {
  return request('/api/commit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
}

// ---------------- 用户照片（AI 试穿底图） ----------------

export async function getUserPhoto() {
  return request('/api/user/photo')
}

export async function uploadUserPhoto(file) {
  const fd = new FormData()
  fd.append('photo', file)
  return request('/api/user/photo', { method: 'POST', body: fd })
}

// ---------------- AI 试穿 ----------------

export async function tryOn(itemIds) {
  return request('/api/tryon', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ itemIds }),
  })
}

/** 保存试穿记录 */
export async function saveTryOnRecord(itemIds, resultUrl) {
  return request('/api/tryon/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ itemIds, resultUrl }),
  })
}

/** 获取试穿记录列表 */
export async function getTryOnRecords() {
  return request('/api/tryon/records')
}

/** 删除试穿记录 */
export async function deleteTryOnRecord(recordId) {
  return request(`/api/tryon/records/${encodeURIComponent(recordId)}`, {
    method: 'DELETE',
  })
}

