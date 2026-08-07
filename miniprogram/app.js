// app.js
const api = require('./utils/api.js')

App({
  globalData: {
    // 后端地址，开发期填你本机局域网 IP + 端口
    // 真机调试时不能填 localhost，必须是本机 IP
    // baseURL: 'https://wardrobe.maidane.com',
    baseURL: 'http://localhost:3000',
    userInfo: null,
    openid: '',
    statusBarHeight: 20,
    windowWidth: 375
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
    // 启动即静默登录，拿到 openid 与用户资料
    this.silentLogin()
  },

  /**
   * 静默登录：wx.login 拿 code -> 后端换 openid -> 拉取资料。
   * 登录失败不阻断主流程（降级为未登录态，由页面引导授权）。
   */
  silentLogin() {
    wx.login({
      success: (res) => {
        if (!res.code) return
        api.login(res.code)
          .then((r) => {
            const openid = r.openid || ''
            const user = r.user || {}
            this.globalData.openid = openid
            this.globalData.userInfo = {
              nickname: user.nickname || '',
              avatar: user.avatar || '',
              createdAt: user.createdAt || 0
            }
            // 通知已在栈中的页面刷新登录态（页面实现 onLoginReady 即可收到）
            const pages = getCurrentPages() || []
            pages.forEach((p) => {
              if (p && typeof p.onLoginReady === 'function') {
                try { p.onLoginReady() } catch (e) { /* ignore */ }
              }
            })
          })
          .catch((e) => console.warn('silent login failed', e.message))
      },
      fail: (e) => console.warn('wx.login failed', e)
    })
  }
})