// pages/user-photo/user-photo.js —— 上传全身正面照
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    userPhoto: '',     // 已上传的全身照（已 fix）
    hasPhoto: false,
    uploading: false
  },

  onShow() {
    this.loadUserPhoto()
  },

  async loadUserPhoto() {
    try {
      const r = await api.getUserPhoto()
      // 后端可能直接返回 photo 信息对象，也可能包一层 {photo: {...}}
      const photo = r && r.photo ? r.photo : (r && (r.url || r.path) ? r : null)
      const url = photo ? fixImage(photo.url || photo) : ''
      this.setData({ userPhoto: url, hasPhoto: !!url })
    } catch (e) { /* ignore */ }
  },

  // 选择 / 拍摄全身正面照
  onChoose() {
    if (this.data.uploading) return
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      camera: 'back',
      sizeType: ['compressed'],
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]
        if (file) this.upload(file.tempFilePath)
      }
    })
  },

  async upload(tempPath) {
    this.setData({ uploading: true })
    try {
      // 发布前内容安全检测（全身照属对外展示图）
      await api.securityCheck('', [tempPath])
      const r = await api.uploadUserPhoto(tempPath)
      // 后端返回 {ok, photo:{url, path, createdAt}}，取 url
      const photo = r && r.photo ? r.photo : (r && (r.url || r.path) ? r : null)
      const url = photo ? fixImage(photo.url || photo) : tempPath
      this.setData({ userPhoto: url, hasPhoto: true, uploading: false })
      wx.showToast({ title: '上传成功', icon: 'success' })
    } catch (e) {
      this.setData({ uploading: false })
      wx.showToast({ title: e.message || '上传失败', icon: 'none' })
    }
  },

  onReupload() {
    this.onChoose()
  }
})
