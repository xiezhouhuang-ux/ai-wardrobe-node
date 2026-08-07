// utils/api.js —— 与后端的 REST 封装

// 注意：不能在模块顶层调用 getApp()，此时 App() 可能尚未注册完成，
// 会返回 undefined 导致全局崩溃。改为在每次请求时动态获取。
function url(path) {
  const app = getApp() || {}
  const base = (app.globalData && app.globalData.baseURL) || ''
  return base + path
}

// 构造带登录态的请求头：Authorization: Bearer <openid>
function authHeader() {
  const app = getApp() || {}
  const openid = (app.globalData && app.globalData.openid) || ''
  if (openid) {
    return { Authorization: 'Bearer ' + openid }
  }
  return {}
}

/**
 * 通用 wx.request Promise 化
 */
function request({ method = 'GET', path, data = {}, header = {}, authRequired = true }) {
  // 需要登录的接口：未登录（无 openid）时直接走未登录处理，避免无效请求。
  // 注意：登录/授权接口本身不能加此守卫，否则永远无法登录（死循环）。
  if (authRequired) {
    const app = getApp() || {}
    const openid = (app.globalData && app.globalData.openid) || ''
    if (!openid) {
      return new Promise((resolve, reject) => {
        const pages = getCurrentPages()
        const cur = pages.length ? pages[pages.length - 1].route : ''
        if (cur !== 'pages/auth/auth') {
          wx.navigateTo({ url: '/pages/auth/auth' })
        }
        reject(new Error('请先登录'))
      })
    }
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url: url(path),
      method,
      data,
      header: Object.assign({ 'Content-Type': 'application/json' }, authHeader(), header),
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // 未登录：跳到授权页（避免对自身页面重复跳转）
          const pages = getCurrentPages()
          const cur = pages.length ? pages[pages.length - 1].route : ''
          if (cur !== 'pages/auth/auth') {
            wx.navigateTo({ url: '/pages/auth/auth' })
          }
          reject(new Error((res.data && res.data.detail) || '请先登录'))
        } else {
          const detail = (res.data && res.data.detail) || `请求失败 (${res.statusCode})`
          reject(new Error(detail))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '网络异常'))
    })
  })
}

/**
 * wx.uploadFile Promise 化
 */
function upload({ path, filePath, name = 'photos', formData = {} }) {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: url(path),
      filePath,
      name,
      formData,
      header: authHeader(),
      success: (res) => {
        try {
          const data = JSON.parse(res.data)
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data)
          } else {
            reject(new Error(data.detail || `上传失败 (${res.statusCode})`))
          }
        } catch (e) {
          reject(new Error('解析响应失败'))
        }
      },
      fail: (err) => reject(new Error(err.errMsg || '上传失败'))
    })
  })
}

module.exports = {
  // 通用
  request,
  upload,

  // 内容安全
  securityCheck: (text, imageUrls) => request({
    method: 'POST', path: '/api/security/check', data: { text: text || '', imageUrls: imageUrls || [] }
  }),

  // 微信授权登录 / 用户资料
  login: (code) => request({ method: 'POST', path: '/api/auth/login', data: { code }, authRequired: false }),
  updateProfile: (openid, nickname, avatar) => request({
    method: 'POST', path: '/api/user/profile', data: { openid, nickname: nickname || '', avatar: avatar || '' }
  }),
  uploadAvatar: (filePath) => upload({ path: '/api/user/avatar', filePath, name: 'avatar' }),

  // 单品
  getConfig: () => request({ path: '/api/config' }),
  getItems: () => request({ path: '/api/items' }),
  getItem: (id) => request({ path: `/api/items/${id}` }),
  deleteItem: (id) => request({ method: 'DELETE', path: `/api/items/${id}` }),
  getStats: () => request({ path: '/api/stats' }),

  // 三步式入库
  analyzePhoto: (filePath) => upload({ path: '/api/analyze', filePath }),
  segmentOne: (photoUrl, item) => request({
    method: 'POST', path: '/api/segment', data: { photoUrl, item }
  }),
  commitItems: (items) => request({
    method: 'POST', path: '/api/commit', data: { items }
  }),

  // 日历穿搭
  getOutfits: (date) => request({ path: date ? `/api/outfits?date=${date}` : '/api/outfits' }),
  saveOutfit: (date, items, note) => request({
    method: 'POST', path: '/api/outfits', data: { date, items, note: note || '' }
  }),
  deleteOutfit: (date) => request({
    method: 'DELETE', path: `/api/outfits/${encodeURIComponent(date)}`
  }),

  // AI 试穿
  getUserPhoto: () => request({ path: '/api/user/photo' }),
  uploadUserPhoto: (filePath) => upload({ path: '/api/user/photo', filePath, name: 'photo' }),
  tryOn: (itemIds) => request({ method: 'POST', path: '/api/tryon', data: { itemIds } }),
  saveTryOnRecord: (itemIds, resultUrl) => request({
    method: 'POST', path: '/api/tryon/save', data: { itemIds, resultUrl }
  }),
  getTryOnRecords: () => request({ path: '/api/tryon/records' }),
  deleteTryOnRecord: (recordId) => request({
    method: 'DELETE', path: `/api/tryon/records/${encodeURIComponent(recordId)}`
  })
}