const KEY = 'tryon_result_cache'

export function setTryOnResultData(data) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(data))
  } catch {
    // ignore
  }
}

export function getTryOnResultData() {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearTryOnResultData() {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}
