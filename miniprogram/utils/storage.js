// utils/storage.js —— 跨页面缓存（替代前端 sessionStorage）
function set(key, value) { wx.setStorageSync(key, value) }
function get(key, fallback = null) {
  const v = wx.getStorageSync(key)
  return v === '' || v === undefined || v === null ? fallback : v
}
function remove(key) { wx.removeStorageSync(key) }

module.exports = { set, get, remove }