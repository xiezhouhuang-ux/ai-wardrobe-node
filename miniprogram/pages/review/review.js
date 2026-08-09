// pages/review/review.js
const api = require('../../utils/api.js')
const storage = require('../../utils/storage.js')
const { categories } = require('../../utils/constants.js')

Page({
  data: {
    items: [],
    categories,
    checkedCount: 0,
    saving: false
  },

  onLoad() {
    const data = storage.get('pendingProcessed') || { items: [] }
    const items = (data.items || []).map(it => {
      const catIdx = Math.max(0, categories.indexOf(it.category))
      // 颜色/风格/季节由 VL 自动识别后直接以文本展示，可手动修改，不再依赖预设字典
      const season = (it.season || '').split(/[、,\s]+/).filter(Boolean).join('、')
      return { ...it, _on: true, catIdx, season, name: it.name || '' }
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
  onColorInput(e) {
    const idx = e.currentTarget.dataset.idx
    this.setData({ [`items[${idx}].color`]: e.detail.value })
  },
  onStyleInput(e) {
    const idx = e.currentTarget.dataset.idx
    this.setData({ [`items[${idx}].style`]: e.detail.value })
  },
  onSeasonInput(e) {
    const idx = e.currentTarget.dataset.idx
    this.setData({ [`items[${idx}].season`]: e.detail.value })
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
        out.color = (it.color || '').trim()
        out.style = (it.style || '').trim()
        out.season = (it.season || '').trim()
        out.name = it.name || ''
        out.imageUrl = it.imageUrl || it.previewUrl
        delete out._on
        delete out.catIdx
        delete out.season
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