// pages/tryon/tryon.js —— AI 试穿（管理视角：选择用户，跳转其衣橱试穿）
const api = require('../../utils/api.js')

Page({
  data: {
    users: [],
    loadingUsers: false,
    error: ''
  },

  onLoad() {
    this.loadUsers()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
  },

  makeInitial(name) {
    const s = (name || '?').trim()
    return s ? s.slice(0, 1) : '?'
  },

  async loadUsers() {
    this.setData({ loadingUsers: true, error: '' })
    try {
      const r = await api.getUsers()
      const me = getApp().globalData.userInfo || {}
      // 自己：昵称/头像取自登录态；openid 优先取后端直接返回的 selfOpenid（JWT 解析，必定可靠）
      const self = r && r.self
      const selfOpenid = (r && r.selfOpenid) || (self && self.openid) || ''
      const selfUser = {
        openid: selfOpenid,
        nickname: me.nickname || (self && self.nickname) || '我',
        avatar: me.avatar || (self && self.avatar) || '',
        isSelf: true,
        initial: this.makeInitial(me.nickname || (self && self.nickname) || '我')
      }
      const list = (r && (r.list || r.items || [])) || []
      const others = (Array.isArray(list) ? list : []).map(u => ({
        ...u,
        isSelf: false,
        initial: this.makeInitial(u.nickname || u.openid || '?')
      }))
      // 自己置顶，与其他用户区分
      this.setData({ users: [selfUser, ...others] })
    } catch (e) {
      this.setData({ error: e.message || '加载用户列表失败', users: [] })
    } finally {
      this.setData({ loadingUsers: false })
    }
  },

  // 进入某用户衣橱试穿（跳转新页面）
  enterWardrobe(e) {
    const openid = e.currentTarget.dataset.openid
    const user = this.data.users.find(u => u.openid === openid)
    if (!user) return
    const params = [
      `openid=${encodeURIComponent(user.openid)}`,
      `nickname=${encodeURIComponent(user.nickname || '')}`,
      `avatar=${encodeURIComponent(user.avatar || '')}`
    ].join('&')
    wx.navigateTo({ url: `/pages/tryon-wardrobe/tryon-wardrobe?${params}` })
  }
})
