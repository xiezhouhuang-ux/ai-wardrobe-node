// pages/calendar/calendar.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

function fmt(y, m, d) {
  const mm = String(m).padStart(2, '0')
  const dd = String(d).padStart(2, '0')
  return `${y}-${mm}-${dd}`
}

function dateDiffDays(a, b) {
  const da = new Date(a + 'T00:00:00')
  const db = new Date(b + 'T00:00:00')
  return Math.round((db - da) / 86400000)
}

function resolveItem(it, realMap) {
  const id = it.itemId || it.id || ''
  const real = realMap[id]
  return {
    id,
    imageUrl: (real && real.image) || it.imageUrl || it.image || '',
    name: (real && (real.color || real.name))
      ? `${real.category || ''}·${real.color || ''}`.replace(/^·/, '')
      : (it.name || it.category || ''),
    category: (real && real.category) || it.category || ''
  }
}

Page({
  data: {
    year: 0,
    month: 0,
    todayD: 0,
    leadingMute: [],
    outfitsByDate: {},
    cells: [], // 日期格子：{ d, dateStr, isToday, has, images:[url] }
    wardrobe: [],
    selectedDay: 0,
    selectedDate: '',
    pickedIds: [],
    saving: false,
    // 分类槽位（与 frontend 一致）
    slots: [
      { cat: '上衣', key: 'top' },
      { cat: '下装', key: 'bottom' },
      { cat: '鞋', key: 'shoes' },
      { cat: '包', key: 'bag' }
    ],
    editing: { top: null, bottom: null, shoes: null, bag: null },
    note: '',
    hasDayOutfit: false,
    pickerCat: '',
    pickerKey: '',
    pickerItems: [],
    // 统计
    mostWorn: null,
    streakItem: null,
    statsDays: 0
  },

  onLoad() {
    const now = new Date()
    this.setStateMonth(now.getFullYear(), now.getMonth() + 1)
    this.loadWardrobe()
  },

  onShow() {
    this.loadOutfits()
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
  },

  setStateMonth(year, month) {
    const total = new Date(year, month, 0).getDate()
    const firstWeekday = new Date(year, month - 1, 1).getDay()
    const today = new Date()
    const isThisMonth = today.getFullYear() === year && (today.getMonth() + 1) === month
    const lead = Array.from({ length: firstWeekday }, (_, i) => i)
    const cells = Array.from({ length: total }, (_, i) => {
      const d = i + 1
      return { d, dateStr: fmt(year, month, d), isToday: isThisMonth && today.getDate() === d, has: false, images: [] }
    })
    this.setData({
      year, month,
      todayD: isThisMonth ? today.getDate() : 0,
      leadingMute: lead,
      cells
    })
    this.loadOutfits()
  },

  onPrev() {
    let m = this.data.month - 1, y = this.data.year
    if (m < 1) { m = 12; y -= 1 }
    this.setStateMonth(y, m)
  },
  onNext() {
    let m = this.data.month + 1, y = this.data.year
    if (m > 12) { m = 1; y += 1 }
    this.setStateMonth(y, m)
  },

  fixImage(u) {
    return fixImage(u)
  },

  async loadWardrobe() {
    try {
      const list = await api.getItems()
      this.setData({ wardrobe: (list || []).map(it => ({ ...it, image: this.fixImage(it.imageUrl || it.image) })) })
    } catch (e) { /* ignore */ }
  },

  async loadOutfits() {
    try {
      const data = await api.getOutfits()
      const map = {}
      ;(data || []).forEach(o => {
        const date = o.date
        if (!date) return
        // 优先取真实衣橱图片，回退到 outfit 里记录的 imageUrl
        const realMap = {}
        for (const it of (this.data.wardrobe || [])) realMap[it.id] = it
        const items = (o.items || []).map(it => {
          const id = it.itemId || it.id
          const real = realMap[id]
          const url = (real && real.image) || it.imageUrl || it.image || ''
          return { ...it, image: this.fixImage(url) }
        })
        // 同一天可能有多条记录，合并 items
        if (map[date]) {
          map[date].items = map[date].items.concat(items)
          if (o.note) map[date].note = o.note
        } else {
          map[date] = { items, note: o.note || '', date }
        }
      })
      const cells = (this.data.cells || []).map(c => {
        const items = (map[c.dateStr] && map[c.dateStr].items) || []
        const images = items.map(it => it.image).filter(Boolean)
        return { ...c, has: images.length > 0, images }
      })
      this.setData({ outfitsByDate: map, cells })
      // 计算月度统计
      this.computeStats(map)
    } catch (e) { /* ignore */ }
  },

  // 计算月度统计（最常穿搭 & 连续穿搭）
  computeStats(outfitsByDate) {
    const { wardrobe } = this.data
    // id -> { name, image } 映射
    const realMap = {}
    for (const it of wardrobe || []) realMap[it.id] = it

    const all = Object.values(outfitsByDate)
    const freq = {} // id -> { count, imageUrl, name }
    for (const rec of all) {
      const items = (rec && rec.items) || []
      for (const it of items) {
        const r = resolveItem(it, realMap)
        if (!r.id) continue
        if (!freq[r.id]) freq[r.id] = { count: 0, imageUrl: r.imageUrl, name: r.name, category: r.category }
        freq[r.id].count++
      }
    }

    // 最常穿搭
    let topItem = null
    for (const id in freq) {
      if (!topItem || freq[id].count > topItem.count) {
        topItem = { itemId: id, ...freq[id] }
      }
    }
    const mostWorn = topItem
      ? { ...topItem, label: `${topItem.name}（${topItem.count} 次）` }
      : null

    // 连续穿搭
    let bestStreak = null
    for (const id in freq) {
      let streak = 0, last = null
      const dates = Object.keys(outfitsByDate).sort()
      for (const ds of dates) {
        const rec = outfitsByDate[ds]
        const has = rec && (rec.items || []).some(it => (it.itemId || it.id) === id)
        if (has) {
          if (last !== null) {
            const diff = dateDiffDays(last, ds)
            if (diff === 1) streak++
            else streak = 1
          } else streak = 1
          last = ds
        }
      }
      if (streak > 0 && (!bestStreak || streak > bestStreak.days)) {
        bestStreak = { itemId: id, days: streak, imageUrl: freq[id].imageUrl, name: freq[id].name }
      }
    }
    const streakItem = bestStreak
      ? { ...bestStreak, label: `${bestStreak.name}（连续 ${bestStreak.days} 天）` }
      : null

    this.setData({
      mostWorn,
      streakItem,
      statsDays: all.length
    })
  },

  fmtDay(d) {
    return fmt(this.data.year, this.data.month, d)
  },

  onSelect(e) {
    const d = e.currentTarget.dataset.d
    const date = fmt(this.data.year, this.data.month, d)
    this.loadDay(date, d)
  },

  onClosePanel() {
    this.setData({ selectedDay: 0, pickerCat: '' })
  },

  // 加载某天的穿搭，按分类填入 editing
  loadDay(date, d) {
    const outfit = this.data.outfitsByDate[date]
    const items = (outfit && outfit.items) || []
    const realMap = {}
    for (const it of (this.data.wardrobe || [])) realMap[it.id] = it
    const map = {}
    for (const it of items) {
      const r = resolveItem(it, realMap)
      map[r.category] = { category: r.category, itemId: r.id, imageUrl: r.imageUrl, name: r.name }
    }
    const editing = {
      top: map['上衣'] || null,
      bottom: map['下装'] || null,
      shoes: map['鞋'] || null,
      bag: map['包'] || null
    }
    this.setData({
      selectedDay: d,
      selectedDate: date,
      editing,
      note: (outfit && outfit.note) || '',
      hasDayOutfit: items.length > 0
    })
  },

  // 打开分类选择面板
  onPickSlot(e) {
    const cat = e.currentTarget.dataset.cat
    const slot = this.data.slots.find(s => s.cat === cat)
    if (!slot) return
    const items = (this.data.wardrobe || []).filter(it => it.category === cat)
    this.setData({ pickerCat: cat, pickerKey: slot.key, pickerItems: items })
  },

  onClosePicker() {
    this.setData({ pickerCat: '' })
  },
  noop() {},

  onPickItem(e) {
    const id = e.currentTarget.dataset.id
    const it = this.data.wardrobe.find(x => x.id === id)
    if (!it) return
    const key = this.data.pickerKey
    const editing = { ...this.data.editing }
    editing[key] = { category: it.category, itemId: it.id, imageUrl: it.image, name: `${it.category}·${it.color || ''}`.replace(/^·/, '') }
    this.setData({ editing, pickerCat: '' })
  },

  onClearSlot(e) {
    const key = e.currentTarget.dataset.key
    const editing = { ...this.data.editing }
    editing[key] = null
    this.setData({ editing })
  },

  onNote(e) {
    this.setData({ note: e.detail.value })
  },

  async onSaveOutfit() {
    const editingItems = this.data.slots
      .map(s => this.data.editing[s.key])
      .filter(Boolean)
      .map(v => ({ category: v.category, itemId: v.itemId, imageUrl: v.imageUrl, name: v.name }))
    if (!editingItems.length) {
      wx.showToast({ title: '请先选择单品', icon: 'none' })
      return
    }
    this.setData({ saving: true })
    try {
      // 发布前内容安全检测（备注文本 + 单品图）
      const imageUrls = editingItems.map(v => v.imageUrl).filter(Boolean)
      await api.securityCheck(this.data.note, imageUrls)
      await api.saveOutfit(this.data.selectedDate, editingItems, this.data.note)
      wx.showToast({ title: '已保存', icon: 'success' })
      this.setData({ selectedDay: 0, pickerCat: '' })
      this.loadOutfits()
    } catch (e) {
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    } finally {
      this.setData({ saving: false })
    }
  },

  onDeleteOutfit() {
    wx.showModal({
      title: '删除当日穿搭',
      content: '确认删除这一天的穿搭记录？',
      confirmColor: '#c96b4a',
      success: async (r) => {
        if (!r.confirm) return
        try {
          await api.deleteOutfit(this.data.selectedDate)
          wx.showToast({ title: '已删除', icon: 'success' })
          this.setData({ selectedDay: 0, pickerCat: '' })
          this.loadOutfits()
        } catch (e) {
          wx.showToast({ title: e.message || '删除失败', icon: 'none' })
        }
      }
    })
  }
})