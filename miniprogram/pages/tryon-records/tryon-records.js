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

  // 点击记录：跳转试穿结果详细页（展示结果图 + 搭配单品）
  onOpenDetail(e) {
    const { id, url, ids } = e.currentTarget.dataset
    if (!url) return
    const params = `recordId=${encodeURIComponent(id || '')}&resultUrl=${encodeURIComponent(url)}&ids=${encodeURIComponent(JSON.stringify(ids || []))}&from=records`
    wx.navigateTo({ url: `/pages/tryon-result/tryon-result?${params}` })
  },

  formatDate(ts) {
    const d = new Date(ts)
    const pad = n => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  }
})
