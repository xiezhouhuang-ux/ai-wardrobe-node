// pages/detail/detail.js
const api = require('../../utils/api.js')
const { categoryColors } = require('../../utils/constants.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    item: null,
    dotColor: '#c96b4a',
    seasonText: '',
    hashList: []
  },

  onLoad(q) { this.itemId = q.id; this.load() },
  onShow() { if (this.itemId) this.load() },

  fixImage(u) {
    return fixImage(u)
  },

  async load() {
    try {
      const it = await api.getItem(this.itemId)
      it.image = this.fixImage(it.imageUrl || it.image)
      it.sourcePhoto = this.fixImage(it.sourcePhoto || '')
      const dotColor = categoryColors[it.category] || '#c96b4a'
      const seasonText = (it.season || '').replace(/[、,\s]+/g, ' · ')
      const hashList = (it.season || '').split(/[、,\s]+/).filter(Boolean)
      this.setData({ item: it, dotColor, seasonText, hashList })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  },

  onBack() { wx.navigateBack() },

  // 点击原图预览：查看原图大图
  onPreviewSource() {
    const src = this.data.item && this.data.item.sourcePhoto
    if (!src) return
    wx.previewImage({
      current: src,
      urls: [src]
    })
  },

  // 用这件单品生成搭配：记录待选中单品，跳转到 AI 搭配页（tabBar，无法传参，借助全局）
  onTryOn() {
    const app = getApp() || {}
    if (app.globalData) app.globalData.pendingTryonItemId = this.itemId
    wx.switchTab({ url: '/pages/tryon/tryon' })
  },

  onDelete() {
    wx.showModal({
      title: '删除确认',
      content: '确认删除这件单品？',
      confirmColor: '#c96b4a',
      success: async (r) => {
        if (!r.confirm) return
        try {
          await api.deleteItem(this.itemId)
          wx.showToast({ title: '已删除', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 600)
        } catch (e) {
          wx.showToast({ title: e.message || '删除失败', icon: 'none' })
        }
      }
    })
  }
})