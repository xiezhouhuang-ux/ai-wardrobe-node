const BASE = import.meta.env.VITE_API_BASE || ''

// 把后端返回的相对路径（/items/...、/uploads/...、/tryon_results/...）拼成可访问 URL
export function fix(url) {
  if (!url) return ''
  if (/^https?:\/\//.test(url)) return url
  return BASE + url
}

export function fmtTime(ts) {
  if (!ts) return '-'
  const d = new Date(Number(ts))
  if (isNaN(d.getTime())) return String(ts)
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
