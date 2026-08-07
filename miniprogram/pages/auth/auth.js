// pages/auth/auth.js
const api = require('../../utils/api.js')

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
            const app = getApp() || {}
            if (app.globalData) {
              app.globalData.openid = r.openid || ''
              app.globalData.userInfo = {
                nickname: (r.user && r.user.nickname) || '',
                avatar: (r.user && r.user.avatar) || '',
                createdAt: (r.user && r.user.createdAt) || 0
              }
            }
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
