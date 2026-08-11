// pages/auth/auth.js
const api = require('../../utils/api.js')
const fixImage = require('../../utils/image.js')
const app = getApp()

Page({
  data: {
    loading: false
  },

  // 点击「微信授权登录」
  onAuth() {
    if (this.data.loading) return
    this.setData({ loading: true })
    wx.login({
      success: (res) => {
        if (!res.code) {
          this.setData({ loading: false })
          wx.showToast({ title: '获取登录凭证失败', icon: 'none' })
          return
        }
        api.login(res.code)
          .then((r) => {
            const token = r.token || ''  // 后端签发的 JWT
            // 先持久化 token，后续 userProfile 请求才带 Authorization
            app.saveLogin(token, {})
            // 登录接口只下发 token/openid，用户信息需额外拉取 /api/user/profile
            return api.userProfile().then((pr) => {
              const u = (pr && pr.user) || {}
              const userInfo = {
                nickname: u.nickname || '',
                avatar: fixImage(u.avatar || ''),
                createdAt: u.createdAt || 0,
                openid: u.openid || ''
              }
              app.saveLogin(token, userInfo)
            }).catch(() => {})
          })
          .then(() => {
            this.setData({ loading: false })
            wx.showToast({ title: '授权成功', icon: 'success' })
            setTimeout(() => {
              // 回到上一页（通常是「我的」）
              wx.navigateBack({
                fail: () => wx.switchTab({ url: '/pages/me/me' })
              })
            }, 600)
          })
          .catch((e) => {
            this.setData({ loading: false })
            wx.showToast({ title: e.message || '授权失败', icon: 'none' })
          })
      },
      fail: () => {
        this.setData({ loading: false })
        wx.showToast({ title: '微信登录失败', icon: 'none' })
      }
    })
  },

  onCancel() {
    wx.navigateBack({
      fail: () => wx.switchTab({ url: '/pages/me/me' })
    })
  }
})
