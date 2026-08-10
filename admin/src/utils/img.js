const BASE = import.meta.env.VITE_API_BASE || ''

// 把后端返回的相对路径（/items/...、/uploads/...、/tryon_results/...）拼成可访问 URL
export function fix(url) {
  if (!url) return ''
  if (/^https?:\/\//.test(url)) return url
  return BASE + url
}

export function fmtTime(ts) {
  if (!ts) return '-'
  let ms = Number(ts)
  if (isNaN(ms)) return String(ts)
  // 兼容秒级（约 1.7e9）与毫秒级（约 1.7e12）时间戳：秒级自动补成毫秒
  if (ms < 1e12) ms *= 1000
  const d = new Date(ms)
  if (isNaN(d.getTime())) return String(ts)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
