// pages/tryon-record-detail/tryon-record-detail.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    recordId: '',
    resultUrl: '',
    saveUrl: '',
    items: [],
    timeText: '',
    loading: true,
    notFound: false
  },

  onLoad(q) {
    const recordId = decodeURIComponent(q.recordId || '')
    this.setData({ recordId })
    this.loadDetail(recordId)
  },

  async loadDetail(recordId) {
    if (!recordId) {
      this.setData({ loading: false, notFound: true })
      return
    }
    this.setData({ loading: true })
    try {
      const rec = await api.getTryOnRecord(recordId)
      if (!rec) {
        this.setData({ loading: false, notFound: true })
        return
      }
      const resultUrl = fixImage(rec.resultUrl)
      const items = (rec.items || []).map(it => ({
        ...it,
        image: fixImage(it.imageUrl || it.image)
      }))
      this.setData({
        resultUrl,
        saveUrl: rec.resultUrl,
        items,
        timeText: this.formatDate(rec.createdAt),
        loading: false,
        notFound: false
      })
    } catch (e) {
      this.setData({ loading: false, notFound: true })
    }
  },

  // 点击结果图直接预览（系统级，可缩放/保存）
  onPreviewImage() {
    const url = this.data.resultUrl
    if (!url) return
    wx.previewImage({ current: url, urls: [url] })
  },

  // 保存到手机相册
  onSaveToAlbum() {
    const url = this.data.resultUrl
    if (!url) return
    wx.showLoading({ title: '保存中…' })
    wx.downloadFile({
      url,
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

  // 点击搭配单品：跳转单品详情页
  onTapItem(e) {
    const { id } = e.currentTarget.dataset
    if (!id) return
    wx.navigateTo({ url: `/pages/detail/detail?id=${encodeURIComponent(id)}` })
  },

  // 删除该试穿记录
  onDeleteRecord() {
    const id = this.data.recordId
    if (!id) return
    wx.showModal({
      title: '确认删除',
      content: '删除后不可恢复',
      confirmColor: '#c96b4a',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.deleteTryOnRecord(id)
          wx.showToast({ title: '已删除', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 500)
        } catch (e) {
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    })
  },

  formatDate(ts) {
    const d = new Date(ts || Date.now())
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
})
