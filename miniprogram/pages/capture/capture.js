// pages/capture/capture.js
const api = require('../../utils/api.js')
const storage = require('../../utils/storage.js')

Page({
  data: {
    tempPath: '',
    analyzing: false
  },

  onPick() { this.choose('album') },
  onPickAlbum() { this.choose('album') },
  onPickCamera() { this.choose('camera') },

  choose(sourceType) {
    if (this.data.analyzing) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: sourceType === 'camera' ? ['camera'] : ['album'],
      sizeType: ['compressed'],
      success: (res) => {
        if (res.tempFiles && res.tempFiles[0]) {
          this.setData({ tempPath: res.tempFiles[0].tempFilePath })
        }
      },
      fail: (err) => {
        // 用户取消不报错
        if (err && err.errMsg && err.errMsg.indexOf('cancel') === -1) {
          wx.showToast({ title: '选择图片失败', icon: 'none' })
        }
      }
    })
  },

  async onConfirm() {
    if (!this.data.tempPath) return
    this.setData({ analyzing: true })
    try {
      const result = await api.analyzePhoto(this.data.tempPath)
      // 后端返回 candidates（候选单品），兼容 items 字段
      const rawItems = result.candidates || result.items || []
      const items = rawItems.map((it, i) => ({
        id: it.id || `c${Date.now()}_${i}`,
        category: it.category || '',
        color: it.color || '',
        style: it.style || '',
        season: it.season || '',
        material: it.material || '',
        name: it.name || ''
      }))
      // photoUrl 用后端返回的相对路径（segment 接口按文件名解析源图）
      const photoUrl = result.photoUrl || ''
      storage.set('pendingAnalysis', {
        photoUrl,
        items,
        tempPath: this.data.tempPath
      })
      // 按前端 /upload 流程：分析后先进入「确认候选单品」页
      wx.navigateTo({ url: '/pages/confirm/confirm' })
    } catch (e) {
      wx.showToast({ title: e.message || '识别失败', icon: 'none' })
    } finally {
      this.setData({ analyzing: false })
    }
  }
})