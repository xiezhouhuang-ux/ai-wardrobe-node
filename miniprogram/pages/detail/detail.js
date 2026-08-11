// pages/detail/detail.js
const api = require('../../utils/api.js')
const { categoryColors } = require('../../utils/constants.js')
const fixImage = require('../../utils/image.js')

Page({
  data: {
    item: null,
    dotColor: '#c96b4a',
    seasonText: '',
    hashList: []
  },

  onLoad(q) { this.itemId = q.id; this.load() },
  onShow() { if (this.itemId) this.load() },

  fixImage(u) {
    return fixImage(u)
  },

  async load() {
    const app = getApp() || {}
    try {
      const it = await api.getItem(this.itemId)
      it.image = this.fixImage(it.imageUrl || it.image)
      it.sourcePhoto = this.fixImage(it.sourcePhoto || '')
      const dotColor = categoryColors[it.category] || '#c96b4a'
      const seasonText = (it.season || '').replace(/[、,\s]+/g, ' · ')
      const hashList = (it.season || '').split(/[、,\s]+/).filter(Boolean)
      // 判断是否本人单品：拉取当前登录用户 openid 与 item.openid 比对
      let isOwner = false
      const cachedOpenid = (app && app.getOpenid && app.getOpenid()) || ''
      if (cachedOpenid) {
        // 登录时已缓存 openid，无需再调 /api/user/profile
        isOwner = !!(it.openid && it.openid === cachedOpenid)
      } else {
        // 兼容旧缓存/未登录场景：回退拉取一次并写回全局
        try {
          const profile = await api.userProfile()
          const myOpenid = (profile && profile.user && profile.user.openid) || ''
          if (myOpenid && app && app.saveLogin) app.saveLogin(app.globalData.token, { openid: myOpenid })
          isOwner = !!(it.openid && myOpenid && it.openid === myOpenid)
        } catch (e) {
          isOwner = false
        }
      }
      this.setData({ item: it, dotColor, seasonText, hashList, isOwner })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
    }
  },

  onBack() { wx.navigateBack() },

  // 点击原图预览：查看原图大图
  onPreviewSource() {
    const src = this.data.item && this.data.item.sourcePhoto
    if (!src) return
    wx.previewImage({
      current: src,
      urls: [src]
    })
  },

  // 用这件单品生成搭配：携带目标用户 openid 与预选单品，跳转衣橱试穿页
  onTryOn() {
    const it = this.data.item || {}
    const openid = it.openid || ''
    if (!openid) {
      wx.showToast({ title: '缺少所属用户', icon: 'none' })
      return
    }
    const params = [
      `openid=${encodeURIComponent(openid)}`,
      `nickname=${encodeURIComponent(it.nickname || '')}`,
      `avatar=${encodeURIComponent(it.avatar || '')}`,
      `initId=${encodeURIComponent(this.itemId)}`
    ].join('&')
    wx.navigateTo({ url: `/pages/tryon-wardrobe/tryon-wardrobe?${params}` })
  },

  onDelete() {
    wx.showModal({
      title: '删除确认',
      content: '确认删除这件单品？',
      confirmColor: '#c96b4a',
      success: async (r) => {
        if (!r.confirm) return
        try {
          await api.deleteItem(this.itemId)
          wx.showToast({ title: '已删除', icon: 'success' })
          setTimeout(() => wx.navigateBack(), 600)
        } catch (e) {
          wx.showToast({ title: e.message || '删除失败', icon: 'none' })
        }
      }
    })
  }
})