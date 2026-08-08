// pages/me/me.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    initial: 'A',
    days: 0,
    createdAt: 0,
    stats: { total: 0, outfits: 0, tryons: 0 },
    userPhoto: '',
    // 登录态
    isLogin: false,
    token: '',  // 登录令牌（JWT），仅用于判断是否已登录
    nickname: '',
    avatarUrl: '',
    showAuth: false,   // 是否展示「点击授权」按钮
    showProfileEdit: false,
    draftNickname: ''
  },

  onLoad() {
    this.setData({ initial: 'A' })
  },

  onShow() {
    this.syncLoginFromGlobal()
    this.loadAll()
  },

  // 静默登录完成后由 app.js 广播：重新同步登录态并刷新数据
  onLoginReady() {
    this.syncLoginFromGlobal()
    this.loadAll()
  },

  // 从全局拉取登录信息（静默登录可能在 onShow 之前完成，也可能之后）
  syncLoginFromGlobal() {
    const app = getApp() || {}
    const { token, userInfo } = app.globalData || {}
    if (token) {
      const nickname = (userInfo && userInfo.nickname) || ''
      const avatarUrl = (userInfo && userInfo.avatar) || ''
      const createdAt = (userInfo && userInfo.createdAt) || 0
      const initial = nickname ? nickname.charAt(0).toUpperCase() : 'A'
      this.setData({
        isLogin: true, token, nickname, avatarUrl, initial,
        createdAt: createdAt,
        days: this.calcDays(createdAt),
        showAuth: !nickname && !avatarUrl  // 已登录但没资料 -> 提示补充
      })
    } else {
      // 未登录：仅更新状态，不主动跳转授权页。
      // 跳转由用户点击「微信授权」按钮触发，避免静默登录异步未完成时反复弹 auth。
      this.setData({ isLogin: false, showAuth: false })
    }
  },

  // 根据真实注册时间（秒级时间戳）计算已陪伴天数
  calcDays(createdAt) {
    if (!createdAt) {
      return 1  // 无注册时间时降级显示
    }
    const start = createdAt * 1000 // 秒级时间戳 -> 毫秒
    const today = Date.now()
    return Math.max(1, Math.floor((today - start) / 86400000))
  },

  async loadAll() {
    try {
      const items = await api.getItems()
      const tryon = await api.getTryOnRecords()
      const outfits = await api.getOutfits()
      this.setData({
        stats: {
          total: (items || []).length,
          outfits: (outfits || []).length,
          tryons: (tryon || []).length
        }
      })
    } catch (e) { /* ignore */ }
    // 全身照状态
    try {
      const r = await api.getUserPhoto()
      const photo = r && r.photo ? r.photo : (r && (r.url || r.path) ? r : null)
      this.setData({ userPhoto: photo ? fixImage(photo.url || photo) : '' })
    } catch (e) { /* 未上传 */ }
  },

  // 点击头像区域：未登录 -> 去授权页；已登录 -> 打开资料编辑
  onTapProfile() {
    if (!this.data.isLogin) {
      wx.navigateTo({ url: '/pages/auth/auth' })
      return
    }
    this.openProfileEdit()
  },

  // 打开「完善资料」弹层（新版微信通过 chooseAvatar + nickname input 合规获取）
  openProfileEdit() {
    this.setData({
      showProfileEdit: true,
      draftNickname: this.data.nickname || ''
    })
  },

  onNicknameInput(e) {
    this.setData({ draftNickname: e.detail.value })
  },

  onChooseAvatar(e) {
    const { avatarUrl } = e.detail
    this.setData({ avatarUrl })
    // 仅上传头像，不关闭弹层（昵称仍待用户输入）
    this.uploadAvatarOnly(avatarUrl)
  },

  async uploadAvatarOnly(avatarUrl) {
    if (!this.data.token || !avatarUrl) return
    let finalAvatar = avatarUrl
    if (!finalAvatar.startsWith('http')) {
      try {
        const up = await api.uploadAvatar(finalAvatar)
        finalAvatar = (up && up.url) || finalAvatar
      } catch (e) {
        wx.showToast({ title: e.message || '头像上传失败', icon: 'none' })
        return
      }
    }
    await this.persistProfile(finalAvatar, this.data.draftNickname)
  },

  onSaveFromSheet() {
    this.saveProfile(this.data.avatarUrl, this.data.draftNickname)
  },

  onCloseEdit() {
    this.setData({ showProfileEdit: false })
  },

  noop() {},

  async saveProfile(avatarUrl, nickname) {
    if (!this.data.token) return
    let finalAvatar = avatarUrl || ''
    // 本地临时文件（wxfile:// 或 http://tmp）需先上传后端换取可访问 URL
    if (finalAvatar && !finalAvatar.startsWith('http')) {
      try {
        const up = await api.uploadAvatar(finalAvatar)
        finalAvatar = (up && up.url) || finalAvatar
      } catch (e) {
        wx.showToast({ title: e.message || '头像上传失败', icon: 'none' })
        return
      }
    }
    await this.persistProfile(finalAvatar, nickname, true)
  },

  // closeSheet: 保存后是否关闭资料弹层
  async persistProfile(finalAvatar, nickname, closeSheet) {
    if (!this.data.token) return
    const app = getApp() || {}
    try {
      const r = await api.updateProfile(nickname || '', finalAvatar || '')
      const user = r.user || {}
      if (app.globalData) {
        app.saveLogin(this.data.token, {
          nickname: user.nickname || '',
          avatar: fixImage(user.avatar || ''),
          createdAt: user.createdAt || this.data.createdAt
        })
      }
      this.setData({
        nickname: user.nickname || '',
        avatarUrl: fixImage(user.avatar || ''),
        initial: (user.nickname || 'A').charAt(0).toUpperCase(),
        createdAt: user.createdAt || this.data.createdAt,
        days: this.calcDays(user.createdAt || this.data.createdAt),
        showAuth: !(user.nickname || user.avatar),
        showProfileEdit: closeSheet ? false : this.data.showProfileEdit
      })
      if (closeSheet) wx.showToast({ title: '已保存', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    }
  },

  onGo(e) {
    const url = e.currentTarget.dataset.url
    wx.switchTab({ url, fail: () => wx.navigateTo({ url }) })
  },

  onTapTryonHistory() {
    wx.navigateTo({ url: '/pages/tryon-records/tryon-records' })
  },

  onTapSettings() {
    wx.showModal({
      title: 'AI 智能衣橱',
      content: '版本 1.0.0\n\n基于大模型的智能衣橱管理应用，支持单品识别、日历穿搭与 AI 试穿。',
      showCancel: false,
      confirmText: '知道了',
      confirmColor: '#c96b4a'
    })
  },

  // 退出登录：清除本地与全局登录态，回到授权页
  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      confirmColor: '#c96b4a',
      success: (res) => {
        if (!res.confirm) return
        const app = getApp() || {}
        if (app.clearLogin) app.clearLogin()
        this.setData({
          isLogin: false, token: '', nickname: '', avatarUrl: '',
          initial: 'A', days: 0, createdAt: 0,
          showAuth: false, showProfileEdit: false
        })
        wx.navigateTo({ url: '/pages/auth/auth' })
      }
    })
  }
})