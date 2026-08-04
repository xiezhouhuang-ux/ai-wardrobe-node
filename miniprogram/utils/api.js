// utils/api.js —— 与后端的 REST 封装
const app = getApp()

function url(path) {
  return app.globalData.baseURL + path
}

/**
 * 通用 wx.request Promise 化
 */
function request({ method = 'GET', path, data = {}, header = {} }) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: url(path),
      method,
      data,
      header: Object.assign({ 'Content-Type': 'application/json' }, header),
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
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

  // 单品
  getConfig: () => request({ path: '/api/config' }),
  getItems: () => request({ path: '/api/items' }),
  getItem: (id) => request({ path: `/api/items/${id}` }),
  deleteItem: (id) => request({ method: 'DELETE', path: `/api/items/${id}` }),
  getStats: () => request({ path: '/api/stats' }),

  // 三步式入库
  analyzePhoto: (filePath) => upload({ path: '/api/analyze', filePath }),
  segmentItems: (photoUrl, items) => request({
    method: 'POST', path: '/api/segment', data: { photoUrl, items }
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