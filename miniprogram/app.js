// app.js
App({
  globalData: {
    // 后端地址，开发期填你本机局域网 IP + 端口
    // 真机调试时不能填 localhost，必须是本机 IP
    baseURL: 'http://10.1.1.222:3000',
    userInfo: null
  },

  onLaunch() {
    // 系统信息：状态栏高度、屏幕宽度等
    try {
      const sys = wx.getSystemInfoSync()
      this.globalData.statusBarHeight = sys.statusBarHeight
      this.globalData.windowWidth = sys.windowWidth
    } catch (e) {
      console.warn('getSystemInfo failed', e)
    }
  }
})