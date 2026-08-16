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
        timeText: this.formatDate(r.createdAt),
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

  // 点击记录：跳转专门的试穿记录详情页（仅传 recordId，详情由后端拉取）
  onOpenDetail(e) {
    const { id } = e.currentTarget.dataset
    if (!id) return
    wx.navigateTo({ url: `/pages/tryon-record-detail/tryon-record-detail?recordId=${encodeURIComponent(id)}` })
  },

  formatDate(ts) {
    const d = new Date(ts)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
})
