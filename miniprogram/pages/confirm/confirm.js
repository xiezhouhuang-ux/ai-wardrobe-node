// pages/confirm/confirm.js —— 入库流程：确认候选单品 + 就地分割处理 + 跳编辑
const api = require('../../utils/api.js')
const storage = require('../../utils/storage.js')
const fixImage = require('../../utils/image.js')

const delay = (ms) => new Promise(r => setTimeout(r, ms))

Page({
  data: {
    photoUrl: '',
    rawPhotoUrl: '',
    candidates: [],
    chosenCount: 0,
    allChecked: true,
    // select: 勾选阶段；processing: 分割处理阶段
    phase: 'select',
    overall: 0,
    error: ''
  },

  onLoad() {
    const pending = storage.get('pendingAnalysis')
    if (!pending || !pending.photoUrl || !pending.items || !pending.items.length) {
      wx.showToast({ title: '没有待确认的数据', icon: 'none' })
      setTimeout(() => wx.navigateBack(), 800)
      return
    }
    const candidates = (pending.items || []).map((it, i) => ({
      ...it,
      _idx: i,
      _on: true,
      _status: 'idle', // idle | pending | done
      categoryLabel: it.category || '单品'
    }))
    this.setData({
      photoUrl: fixImage(pending.photoUrl),
      rawPhotoUrl: pending.photoUrl,
      candidates,
      chosenCount: candidates.length,
      allChecked: true
    })
  },

  toggleItem(e) {
    if (this.data.phase !== 'select') return
    const idx = e.currentTarget.dataset.index
    const key = `candidates[${idx}]._on`
    const next = !this.data.candidates[idx]._on
    this.setData({ [key]: next })
    this.refreshSelection()
  },

  // 点击已分割单品的缩略图，放大预览（catchtap 已阻止冒泡，不会触发勾选）
  onPreviewItem(e) {
    const url = e.currentTarget.dataset.url
    if (!url) return
    wx.previewImage({ current: url, urls: [url] })
  },

  toggleAll() {
    if (this.data.phase !== 'select') return
    const next = !this.data.allChecked
    const candidates = this.data.candidates.map(c => ({ ...c, _on: next }))
    this.setData({ candidates, allChecked: next })
    this.refreshSelection()
  },

  refreshSelection() {
    const chosen = this.data.candidates.filter(c => c._on).length
    const all = this.data.candidates.length > 0 && this.data.candidates.every(c => c._on)
    this.setData({ chosenCount: chosen, allChecked: all })
  },

  onReupload() {
    storage.remove('pendingAnalysis')
    storage.remove('pendingProcessed')
    wx.navigateBack()
  },

  async onConfirm() {
    if (this.data.phase !== 'select') return
    const chosen = this.data.candidates.filter(c => c._on)
    if (!chosen.length) {
      this.setData({ error: '请至少勾选一个单品' })
      return
    }
    this.setData({ phase: 'processing', error: '', overall: 0 })

    // 标记勾选项为处理中
    const candidates = this.data.candidates.map(c =>
      c._on ? { ...c, _status: 'pending' } : c
    )
    this.setData({ candidates })

    try {
      const processed = []
      for (let i = 0; i < chosen.length; i++) {
        const item = chosen[i]
        const idx = item._idx
        this.setData({
          [`candidates[${idx}]._status`]: 'pending',
          overall: Math.round((i / chosen.length) * 100)
        })
        // 每次仅上传一件单品进行分割
        const seg = await api.segmentOne(this.data.rawPhotoUrl, item)
        // 保留前端展示字段，合并后端返回的分割结果
        const merged = {
          ...item,
          ...seg,
          previewUrl: fixImage(seg.imageUrl || seg.image || ''),
          category: seg.category || item.category || '上装',
          color: seg.color || item.color || '',
          style: seg.style || item.style || '',
          season: seg.season || item.season || '',
          name: seg.name || item.name || ''
        }
        processed.push(merged)
        this.setData({
          [`candidates[${idx}]._status`]: 'done',
          overall: Math.round(((i + 1) / chosen.length) * 100)
        })
      }

      storage.set('pendingProcessed', {
        photoUrl: this.data.rawPhotoUrl,
        items: processed
      })
      setTimeout(() => {
        wx.redirectTo({ url: '/pages/review/review' })
      }, 450)
    } catch (e) {
      this.setData({ phase: 'select', error: e.message || '分割失败' })
    }
  }
})
