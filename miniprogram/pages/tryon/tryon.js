// pages/tryon/tryon.js —— AI 试穿（按分类选择衣橱单品，与 frontend 逻辑一致）
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

const CATEGORIES = ['上衣', '下装', '鞋', '包']

Page({
  data: {
    userPhoto: '',
    wardrobe: [],
    groupList: [],       // [{ cat, items: [...] }]
    selected: {},       // { '上衣': itemId, '下装': itemId, ... }
    selectedItems: [],  // 已选单品详情（按 CATEGORIES 顺序）
    categories: CATEGORIES,
    generating: false,
    error: ''
  },

  onLoad() {
    this.loadUserPhoto()
    this.loadWardrobe()
  },

  onShow() {
    // 每次展示时刷新数据
    this.loadUserPhoto()
    this.loadWardrobe()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
  },

  fixImage(u) {
    return fixImage(u)
  },

  async loadUserPhoto() {
    try {
      const r = await api.getUserPhoto()
      // 后端可能返回 {photo:{url}} 或 {url, path}，需兼容对象与字符串两种形态
      const photo = r && r.photo ? r.photo : (r && (r.url || r.path) ? r : null)
      const url = photo ? this.fixImage(photo.url || photo) : ''
      this.setData({ userPhoto: url })
    } catch (e) { /* ignore */ }
  },

  async loadWardrobe() {
    try {
      const list = await api.getItems()
      const items = (list || []).map(it => ({
        ...it,
        image: this.fixImage(it.imageUrl || it.image)
      }))
      // 按分类分组（仅展示有定义的四类）
      const map = {}
      for (const c of CATEGORIES) map[c] = []
      const others = []
      for (const it of items) {
        const cat = it.category
        if (map[cat]) map[cat].push(it)
        else others.push(it)
      }
      const groupList = CATEGORIES.map(cat => ({ cat, items: map[cat] }))
      this.setData({ wardrobe: items, groupList })
    } catch (e) { /* ignore */ }
  },

  onUploadUser() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: async (res) => {
        if (!res.tempFiles || !res.tempFiles[0]) return
        try {
          wx.showLoading({ title: '上传中…' })
          const r = await api.uploadUserPhoto(res.tempFiles[0].tempFilePath)
          this.setData({ userPhoto: this.fixImage(r.photo) })
        } catch (e) {
          wx.showToast({ title: e.message || '上传失败', icon: 'none' })
        } finally {
          wx.hideLoading()
        }
      }
    })
  },

  goToMe() {
    wx.navigateTo({ url: '/pages/user-photo/user-photo' })
  },

  // 点击某分类下的单品：单选（再次点击取消）
  onToggleSelect(e) {
    const { cat, id } = e.currentTarget.dataset
    const selected = Object.assign({}, this.data.selected)
    if (selected[cat] === id) delete selected[cat]
    else selected[cat] = id
    this.updateSelectedItems(selected)
  },

  isSelected(cat, id) {
    return this.data.selected[cat] === id
  },

  updateSelectedItems(selected) {
    const wardrobe = this.data.wardrobe
    const selectedItems = []
    for (const cat of CATEGORIES) {
      const id = selected[cat]
      if (!id) continue
      const it = wardrobe.find(i => i.id === id)
      if (it) selectedItems.push(it)
    }
    this.setData({ selected, selectedItems })
  },

  // 生成试穿
  async onGenerate() {
    if (!this.data.userPhoto) {
      wx.showToast({ title: '请先上传全身照', icon: 'none' })
      return
    }
    const ids = CATEGORIES.map(c => this.data.selected[c]).filter(Boolean)
    if (!ids.length) {
      wx.showToast({ title: '请选择单品', icon: 'none' })
      return
    }
    this.setData({ generating: true, error: '' })
    try {
      const r = await api.tryOn(ids)
      const resultUrl = this.fixImage(r.resultUrl)
      wx.navigateTo({
        url: `/pages/tryon-result/tryon-result?resultUrl=${encodeURIComponent(r.resultUrl)}&ids=${encodeURIComponent(JSON.stringify(ids))}`
      })
    } catch (e) {
      this.setData({ error: e.message || '试穿生成失败，请重试' })
    } finally {
      this.setData({ generating: false })
    }
  },

  onReset() {
    this.setData({ selected: {}, selectedItems: [], error: '' })
  }
})
