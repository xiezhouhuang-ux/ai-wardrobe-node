// pages/tryon-result/tryon-result.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    resultUrl: '',      // 显示用（经过 fixImage 处理）
    saveUrl: '',        // 保存用（本地路径）
    ids: [],
    outfitItems: [],    // 搭配单品详情
    saving: false,
    saved: false
  },
  onLoad(q) {
    const saveUrl = decodeURIComponent(q.resultUrl || '')
    this.setData({
      resultUrl: fixImage(saveUrl),
      saveUrl,
      ids: q.ids ? JSON.parse(decodeURIComponent(q.ids)) : []
    })
    this.loadOutfitItems()
  },

  fixImg(u) {
    return fixImage(u)
  },

  async loadOutfitItems() {
    if (!this.data.ids.length) return
    try {
      const items = await api.getItems()
      const map = {}
      for (const it of (items || [])) {
        map[it.id] = { ...it, image: this.fixImg(it.imageUrl || it.image) }
      }
      const outfitItems = this.data.ids.map(id => map[id] || { id, name: '单品', category: '上装', image: '' }).filter(it => it.id)
      this.setData({ outfitItems })
    } catch (e) { /* ignore */ }
  },

  // 确认保存：将本地结果图归档到数据库记录
  async onConfirmSave() {
    if (this.data.saving || this.data.saved) return
    const { saveUrl, ids } = this.data
    if (!saveUrl || !ids.length) {
      wx.showToast({ title: '缺少结果图或单品信息', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      await api.saveTryOnRecord(ids, saveUrl)
      this.setData({ saved: true })
      wx.showToast({ title: '已保存到试穿记录', icon: 'success' })
    } catch (e) {
      // 内容违规时后端返回 detail="所发布内容含违规信息"，原文透传；其余错误沿用通用提示
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },

  // 保存到手机相册
  onSaveToAlbum() {
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

  // 点击结果图直接预览（系统级，可缩放/保存）
  onPreviewImage() {
    const url = this.data.resultUrl
    if (!url) return
    wx.previewImage({ current: url, urls: [url] })
  }
})