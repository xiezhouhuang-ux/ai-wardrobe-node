// components/nav-bar/nav-bar.js
const nav = require('../../utils/nav.js')

Component({
  options: { multipleSlots: true },
  properties: {
    title: { type: String, value: '' },
    back: { type: Boolean, value: false },
    transparent: { type: Boolean, value: false }
  },
  data: {
    statusBarHeight: 20,
    navBarHeight: 64,
    totalHeight: 84
  },
  lifetimes: {
    attached() {
      const statusBarHeight = nav.getStatusBarHeight()
      const navBarHeight = nav.getNavBarHeight()
      const totalHeight = statusBarHeight + navBarHeight
      this.setData({ statusBarHeight, navBarHeight, totalHeight })
    }
  },
  methods: {
    onBack() {
      wx.navigateBack({ delta: 1, fail: () => wx.switchTab({ url: '/pages/home/home' }) })
    }
  }
})