// pages/home/home.js
const api = require('../../utils/api.js')
const { categories } = require('../../utils/constants.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    items: [],
    filtered: [],
    categories,
    activeCat: '',
    keyword: '',
    loading: true,
    greetText: '',
    now: '',
    stats: { tryonCount: 0 }
  },

  onLoad() {
    this.setGreeting()
  },

  onShow() {
    this.loadItems()
    this.loadStats()
  },

  onPullDownRefresh() {
    this.loadItems().then(() => wx.stopPullDownRefresh())
  },

  setGreeting() {
    const d = new Date()
    const h = d.getHours()
    const mm = String(d.getMinutes()).padStart(2, '0')
    this.setData({ now: `${h}:${mm}` })
    // 根据时段显示不同问候
    if (h < 6) this.setData({ greetText: '夜深了' })
    else if (h < 12) this.setData({ greetText: '早上好' })
    else if (h < 14) this.setData({ greetText: '中午好' })
    else if (h < 18) this.setData({ greetText: '下午好' })
    else this.setData({ greetText: '晚上好' })
  },

  async loadStats() {
    try {
      const stats = await api.getStats()
      this.setData({ stats: stats || {} })
    } catch (e) { /* ignore */ }
  },

  async loadItems() {
    this.setData({ loading: true })
    try {
      const items = await api.getItems()
      // 给后端相对路径的图片加 baseURL（后端字段为 imageUrl）
      const mapped = (items || []).map(it => ({
        ...it,
        image: this.fixImage(it.imageUrl || it.image)
      }))
      this.setData({ items: mapped }, () => this.applyFilter())
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
    }
  },

  fixImage(url) {
    return fixImage(url)
  },

  applyFilter() {
    const { items, activeCat, keyword } = this.data
    const kw = keyword.trim().toLowerCase()
    const filtered = items.filter(it => {
      if (activeCat && it.category !== activeCat) return false
      if (!kw) return true
      const text = `${it.category || ''} ${it.color || ''} ${it.style || ''} ${it.name || ''}`.toLowerCase()
      return text.includes(kw)
    })
    this.setData({ filtered })
  },

  onSelectCat(e) {
    const cat = e.currentTarget.dataset.cat
    this.setData({ activeCat: cat }, () => this.applyFilter())
  },

  onSearch(e) {
    this.setData({ keyword: e.detail.value }, () => this.applyFilter())
  },

  onTapItem(e) {
    if (this._navigating) return
    const src = (e.detail && e.detail.item) ? e.detail.item : (this.data.filtered[e.currentTarget.dataset.index] || {})
    const id = src.id || src._id || e.currentTarget.dataset.id
    if (!id) {
      wx.showToast({ title: '单品数据异常', icon: 'none' })
      return
    }
    this._navigating = true
    wx.navigateTo({ url: `/pages/detail/detail?id=${id}` })
    setTimeout(() => { this._navigating = false }, 800)
  },

  onTapAdd() { this.onTapFab() },
  onTapFab() {
    wx.navigateTo({ url: '/pages/capture/capture' })
  }
})