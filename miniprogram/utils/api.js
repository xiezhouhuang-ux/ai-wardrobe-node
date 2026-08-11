// utils/api.js —— 与后端的 REST 封装

// 注意：不能在模块顶层调用 getApp()，此时 App() 可能尚未注册完成，
// 会返回 undefined 导致全局崩溃。改为在每次请求时动态获取。
function url(path) {
  const app = getApp() || {}
  const base = (app.globalData && app.globalData.baseURL) || ''
  return base + path
}

// 获取登录令牌（JWT）：优先取全局，回退本地存储（适配全局尚未初始化的场景）
function getToken() {
  const app = getApp() || {}
  const fromGlobal = app.globalData && app.globalData.token
  if (fromGlobal) return fromGlobal
  try {
    const local = wx.getStorageSync('login_token')
    if (local) return local
  } catch (e) { /* ignore */ }
  return ''
}

function authHeader() {
  const token = getToken()
  if (token) {
    return { Authorization: 'Bearer ' + token }
  }
  return {}
}

// 跳转到授权页（仅由用户显式操作触发，例如「微信授权登录」/「退出登录」后）。
// 注意：不再在请求拦截里自动跳转，避免未登录时进入首页/我的页被反复弹到 auth 页。
function gotoAuth() {
  const pages = getCurrentPages() || []
  const cur = pages.length ? pages[pages.length - 1].route : ''
  if (cur === 'pages/auth/auth') return
  wx.navigateTo({ url: '/pages/auth/auth' })
}

/**
 * 通用 wx.request Promise 化
 */
function request({ method = 'GET', path, data = {}, header = {}, authRequired = true }) {
  // 需要登录的接口：未登录（无 token）时直接以「请先登录」拒绝，不再自动跳转授权页。
  // 登录/授权（api.login）本身 authRequired:false，不会被此守卫拦截。
  if (authRequired) {
    const token = getToken()
    if (!token) {
      gotoAuth()
      return Promise.reject(new Error('请先登录'))
    }
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url: url(path),
      method,
      data,
      timeout: 5 * 60 * 1000,
      header: Object.assign({ 'Content-Type': 'application/json' }, authHeader(), header),
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          // 登录态失效：仅拒绝，由调用方决定是否引导登录（不再自动跳 auth 页）
          if(authRequired ){
            gotoAuth()
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
function upload({ path, filePath, name = 'photos', formData = {}, authRequired = true }) {
  // 需要登录态时校验：缺少 token 视为未登录（login 接口本身 authRequired:false）
  if (authRequired && !getToken()) {
    gotoAuth();
    return Promise.reject(new Error('请先登录'))
  }
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: url(path),
      filePath,
      name,
      formData,
      timeout: 5 * 60 * 1000,
      header: authHeader(),
      success: (res) => {
        try {
          const data = JSON.parse(res.data)
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data)
          } else if (res.statusCode === 401) {
            // 登录态失效：仅拒绝，由调用方引导登录（不再自动跳 auth 页）
            gotoAuth();
            reject(new Error(data.detail || '请先登录'))
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
  userProfile: () => request({ path: '/api/user/profile', authRequired: true }),
  updateProfile: (nickname, avatar) => request({
    method: 'POST', path: '/api/user/profile', data: { nickname: nickname || '', avatar: avatar || '' }
  }),
  uploadAvatar: (filePath) => upload({ path: '/api/user/avatar', filePath, name: 'avatar' }),

  // 单品
  getConfig: () => request({ path: '/api/config' }),
  getItems: (target) => request({ path: target ? `/api/items?target=${encodeURIComponent(target)}` : '/api/items', authRequired: false }),
  getItem: (id) => request({ path: `/api/items/${id}` }),

  // 用户（管理视角：供切换用户衣橱试穿）
  getUsers: (page = 1, size = 200) => request({ path: `/api/users?page=${page}&size=${size}`, authRequired: true }),
  deleteItem: (id) => request({ method: 'DELETE', path: `/api/items/${id}` }),
  getStats: () => request({ path: '/api/stats' , authRequired: false }),

  // 三步式入库
  analyzePhoto: (filePath) => upload({ path: '/api/analyze', filePath }),
  segmentOne: (photoUrl, item) => request({
    method: 'POST', path: '/api/segment', data: { photoUrl, item }
  }),
  commitItems: (items) => request({
    method: 'POST', path: '/api/commit', data: { items }
  }),

  // 日历穿搭
  getOutfits: (date) => request({ path: date ? `/api/outfits?date=${date}` : '/api/outfits' , authRequired: false }),
  saveOutfit: (date, items, note) => request({
    method: 'POST', path: '/api/outfits', data: { date, items, note: note || '' }
  }),
  deleteOutfit: (date) => request({
    method: 'DELETE', path: `/api/outfits/${encodeURIComponent(date)}`
  }),

  // AI 试穿
  getUserPhoto: (target) => request({ path: target ? `/api/user/photo?target=${encodeURIComponent(target)}` : '/api/user/photo', authRequired: false }),
  uploadUserPhoto: (filePath) => upload({ path: '/api/user/photo', filePath, name: 'photo', authRequired: true }),
  tryOn: (itemIds, target) => request({ method: 'POST', path: '/api/tryon', data: { itemIds, target: target || '' } }),
  saveTryOnRecord: (itemIds, resultUrl, target) => request({
    method: 'POST', path: '/api/tryon/save', data: { itemIds, resultUrl, target: target || '' }
  }),
  getTryOnRecords: () => request({ path: '/api/tryon/records' , authRequired: false}),
  deleteTryOnRecord: (recordId) => request({
    method: 'DELETE', path: `/api/tryon/records/${encodeURIComponent(recordId)}`
  })
}