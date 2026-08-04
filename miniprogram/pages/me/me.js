// pages/me/me.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    initial: 'A',
    days: 0,
    stats: { total: 0, outfits: 0, tryons: 0 },
    userPhoto: ''
  },

  onLoad() {
    this.setData({ initial: 'A', days: this.calcDays() })
  },

  onShow() { this.loadAll() },

  calcDays() {
    const start = new Date('2025-01-01').getTime()
    const today = Date.now()
    return Math.max(1, Math.floor((today - start) / 86400000))
  },

  async loadAll() {
    try {
      const items = await api.getItems()
      const tryon = await api.getTryOnRecords()
      const outfits = await api.getOutfits()
      this.setData({
        stats: {
          total: (items || []).length,
          outfits: (outfits || []).length,
          tryons: (tryon || []).length
        }
      })
    } catch (e) { /* ignore */ }
    // 全身照状态
    try {
      const r = await api.getUserPhoto()
      const photo = r && r.photo ? r.photo : (r && (r.url || r.path) ? r : null)
      this.setData({ userPhoto: photo ? fixImage(photo.url || photo) : '' })
    } catch (e) { /* 未上传 */ }
  },

  onGo(e) {
    const url = e.currentTarget.dataset.url
    wx.switchTab({ url, fail: () => wx.navigateTo({ url }) })
  },

  onTapTryonHistory() {
    wx.navigateTo({ url: '/pages/tryon-records/tryon-records' })
  },

  onTapSettings() {
    wx.showModal({
      title: 'AI 智能衣橱',
      content: '版本 1.0.0\n\n基于大模型的智能衣橱管理应用，支持单品识别、日历穿搭与 AI 试穿。',
      showCancel: false,
      confirmText: '知道了',
      confirmColor: '#c96b4a'
    })
  }
})