// pages/review/review.js
const api = require('../../utils/api.js')
const storage = require('../../utils/storage.js')
const { categories, colors, styles, seasons } = require('../../utils/constants.js')

Page({
  data: {
    items: [],
    categories,
    colors,
    styles,
    seasonsList: seasons,
    checkedCount: 0,
    saving: false
  },

  onLoad() {
    const data = storage.get('pendingProcessed') || { items: [] }
    const items = (data.items || []).map(it => {
      const catIdx = Math.max(0, categories.indexOf(it.category))
      const colorIdx = Math.max(0, colors.indexOf(it.color))
      const styleIdx = Math.max(0, styles.indexOf(it.style))
      const seasonsList = (it.season || '').split(/[、,\s]+/).filter(Boolean)
      const picked = seasonsList.length ? seasonsList : ['春', '秋']
      return { ...it, _on: true, catIdx, colorIdx, styleIdx, seasons: picked, name: '' }
    })
    this.setData({ items })
    this.refreshChecked(items)
  },

  toggleItem(e) {
    const idx = e.currentTarget.dataset.index
    const key = `items[${idx}]._on`
    this.setData({ [key]: !this.data.items[idx]._on })
    this.refreshChecked()
  },

  refreshChecked(list) {
    const arr = list || this.data.items
    const checkedCount = (arr || []).filter(it => it._on).length
    this.setData({ checkedCount })
  },

  onNameInput(e) {
    const idx = e.currentTarget.dataset.idx
    const key = `items[${idx}].name`
    this.setData({ [key]: e.detail.value })
  },

  onChangeCat(e) {
    const idx = e.currentTarget.dataset.idx
    const key = `items[${idx}].catIdx`
    this.setData({ [key]: Number(e.detail.value) })
  },
  onChangeColor(e) {
    const idx = e.currentTarget.dataset.idx
    const key = `items[${idx}].colorIdx`
    this.setData({ [key]: Number(e.detail.value) })
  },
  onChangeStyle(e) {
    const idx = e.currentTarget.dataset.idx
    const key = `items[${idx}].styleIdx`
    this.setData({ [key]: Number(e.detail.value) })
  },

  onToggleSeason(e) {
    const idx = e.currentTarget.dataset.idx
    const s = e.currentTarget.dataset.s
    const items = this.data.items.slice()
    const set = new Set(items[idx].seasons || [])
    if (set.has(s)) set.delete(s); else set.add(s)
    items[idx].seasons = Array.from(set)
    this.setData({ items })
  },

  async onSave() {
    const checked = this.data.items.filter(it => it._on)
    if (!checked.length) {
      wx.showToast({ title: '请至少勾选一件', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      const items = checked.map(it => {
        // 保留分割阶段返回的全部原始字段（material/fit/pattern/
        // sourcePhoto/transparent/segmentMethod/imagePath/id 等），
        // 仅覆盖用户在 UI 上可编辑的字段，并剔除前端专用索引字段
        const out = { ...it }
        out.category = this.data.categories[it.catIdx]
        out.color = this.data.colors[it.colorIdx] || ''
        out.style = this.data.styles[it.styleIdx] || ''
        out.season = (it.seasons || []).join('、')
        out.name = it.name || ''
        out.imageUrl = it.imageUrl || it.previewUrl
        delete out._on
        delete out.catIdx
        delete out.colorIdx
        delete out.styleIdx
        delete out.seasons
        delete out.previewUrl
        return out
      })
      await api.commitItems(items)
      storage.remove('pendingAnalysis')
      storage.remove('pendingProcessed')
      wx.showToast({ title: '已保存', icon: 'success' })
      setTimeout(() => wx.switchTab({ url: '/pages/home/home' }), 800)
    } catch (e) {
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  }
})