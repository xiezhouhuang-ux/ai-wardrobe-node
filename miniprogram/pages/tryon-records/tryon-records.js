// pages/tryon-records/tryon-records.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    records: [],
    loading: false,
    empty: false
  },

  onShow() {
    this.loadRecords()
    // 支持下拉刷新
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: null })
    }
  },

  onPullDownRefresh() {
    this.loadRecords().then(() => wx.stopPullDownRefresh())
  },

  async loadRecords() {
    this.setData({ loading: true })
    try {
      const records = await api.getTryOnRecords()
      // 统一拼接 resultUrl，保证列表图片显示
      const fixed = (records || []).map(r => ({
        ...r,
        resultUrl: fixImage(r.resultUrl),
        items: (r.items || []).map(it => ({ ...it, image: fixImage(it.imageUrl || it.image) }))
      }))
      this.setData({
        records: fixed,
        empty: !records || records.length === 0,
        loading: false
      })
    } catch (e) {
      this.setData({
        records: [],
        empty: true,
        loading: false
      })
    }
  },

  // 点击记录：直接查看试穿图片（系统级预览，可缩放/保存）
  onViewResult(e) {
    const { url } = e.currentTarget.dataset
    if (!url) return
    wx.previewImage({ current: url, urls: [url] })
  },

  onDelete(e) {
    const { id } = e.currentTarget.dataset
    wx.showModal({
      title: '确认删除',
      content: '删除后不可恢复',
      confirmColor: '#c96b4a',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.deleteTryOnRecord(id)
          const records = this.data.records.filter(r => r.id !== id)
          this.setData({
            records,
            empty: records.length === 0
          })
          wx.showToast({ title: '已删除', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: '删除失败', icon: 'none' })
        }
      }
    })
  },

  formatDate(ts) {
    const d = new Date(ts)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
})
