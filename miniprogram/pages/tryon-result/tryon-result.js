// pages/tryon-result/tryon-result.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    resultUrl: '',
    ids: [],
    outfitItems: []  // 搭配单品详情
  },
  onLoad(q) {
    this.setData({
      resultUrl: decodeURIComponent(q.resultUrl || ''),
      ids: q.ids ? JSON.parse(decodeURIComponent(q.ids)) : []
    })
    this.loadOutfitItems()
  },

  fixImage(u) {
    return fixImage(u)
  },

  async loadOutfitItems() {
    if (!this.data.ids.length) return
    try {
      const items = await api.getItems()
      const map = {}
      for (const it of (items || [])) {
        map[it.id] = { ...it, image: this.fixImage(it.imageUrl || it.image) }
      }
      const outfitItems = this.data.ids.map(id => map[id] || { id, name: '单品', category: '上装', image: '' }).filter(it => it.id)
      this.setData({ outfitItems })
    } catch (e) { /* ignore */ }
  },

  onSave() {
    if (!this.data.resultUrl) return
    wx.showLoading({ title: '保存中…' })
    wx.downloadFile({
      url: this.data.resultUrl,
      success: (res) => {
        wx.saveImageToPhotosAlbum({
          filePath: res.tempFilePath,
          success: () => wx.showToast({ title: '已保存', icon: 'success' }),
          fail: () => wx.showToast({ title: '保存失败', icon: 'none' })
        })
      },
      fail: () => wx.showToast({ title: '下载失败', icon: 'none' }),
      complete: () => wx.hideLoading()
    })
  },
  onRetry() { wx.navigateBack() }
})