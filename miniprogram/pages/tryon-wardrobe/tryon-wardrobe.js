// pages/tryon-wardrobe/tryon-wardrobe.js —— 进入某用户衣橱选单品试穿
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

const CATEGORIES = ['上衣', '下装', '鞋', '包']

Page({
  data: {
    currentUser: null,   // { openid, nickname, avatar, initial }

    userPhoto: '',
    wardrobe: [],
    groupList: [],       // [{ cat, items: [...] }]
    selected: {},       // { '上衣': itemId, '下装': itemId, ... }
    selectedItems: [],  // 已选单品详情（按 CATEGORIES 顺序）
    categories: CATEGORIES,
    loadingWardrobe: false,
    generating: false,
    error: ''
  },

  onLoad(q) {
    const openid = decodeURIComponent(q.openid || '')
    const nickname = q.nickname ? decodeURIComponent(q.nickname) : ''
    const avatar = q.avatar ? decodeURIComponent(q.avatar) : ''
    const user = {
      openid,
      nickname,
      avatar,
      initial: this.makeInitial(nickname || openid || '?')
    }
    this.setData({ currentUser: user })
    this.loadWardrobe(openid)
  },

  fixImage(u) {
    return fixImage(u)
  },

  makeInitial(name) {
    const s = (name || '?').trim()
    return s ? s.slice(0, 1) : '?'
  },

  async loadWardrobe(target) {
    if (!target) return
    this.setData({ loadingWardrobe: true, error: '' })
    try {
      const [items, photo] = await Promise.all([
        api.getItems(target),
        api.getUserPhoto(target).catch(() => null)
      ])
      const list = (items || []).map(it => ({
        ...it,
        image: this.fixImage(it.imageUrl || it.image)
      }))
      // 按分类分组（仅展示有定义的四类）
      const map = {}
      for (const c of CATEGORIES) map[c] = []
      for (const it of list) {
        const cat = it.category
        if (map[cat]) map[cat].push(it)
      }
      const groupList = CATEGORIES.map(cat => ({ cat, items: map[cat] }))
      this.setData({ wardrobe: list, groupList })
      // 目标用户全身照（404 视为未上传）
      const url = photo ? this.fixImage(photo.url || photo.path || photo) : ''
      this.setData({ userPhoto: url })
    } catch (e) {
      this.setData({ error: e.message || '加载衣橱失败', userPhoto: '' })
    } finally {
      this.setData({ loadingWardrobe: false })
    }
  },

  // 点击某分类下的单品：单选（再次点击取消）
  onToggleSelect(e) {
    const { cat, id } = e.currentTarget.dataset
    const selected = Object.assign({}, this.data.selected)
    if (selected[cat] === id) delete selected[cat]
    else selected[cat] = id
    this.updateSelectedItems(selected)
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

  // 生成试穿（带 target openid）
  async onGenerate() {
    if (!this.data.userPhoto) {
      wx.showToast({ title: '该用户未上传全身照', icon: 'none' })
      return
    }
    const ids = CATEGORIES.map(c => this.data.selected[c]).filter(Boolean)
    if (!ids.length) {
      wx.showToast({ title: '请选择单品', icon: 'none' })
      return
    }
    const target = this.data.currentUser.openid
    this.setData({ generating: true, error: '' })
    try {
      const r = await api.tryOn(ids, target)
      const resultUrl = r.resultUrl
      wx.navigateTo({
        url: `/pages/tryon-result/tryon-result?resultUrl=${encodeURIComponent(resultUrl)}&ids=${encodeURIComponent(JSON.stringify(ids))}&target=${encodeURIComponent(target)}`
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
