// app.js
const api = require('./utils/api.js')
const fixImage = require('./utils/image.js')
const storage = require('./utils/storage.js')

App({
  globalData: {
    // 后端地址，开发期填你本机局域网 IP + 端口
    // 真机调试时不能填 localhost，必须是本机 IP
    baseURL: 'https://wardrobe.maidane.com',
    // 注意：小程序运行在微信客户端，localhost 指向手机自身而非后端电脑，
    // 必须填后端电脑的局域网 IP（开发者工具/真机调试需勾选“不校验合法域名”）。
    // baseURL: 'http://10.1.1.222:3000',
    userInfo: { nickname: '', avatar: '', createdAt: 0 },
    token: '', // 登录令牌（JWT），请求时放在 Authorization 头
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
    // 先尝试从本地恢复登录态（重启小程序后无需重新授权即可登录）
    this.restoreLogin()
    // 再静默登录刷新最新资料与 token
    this.silentLogin()
  },

  // 从本地存储恢复登录态到全局（持久化的是 JWT，openid 不再下发到前端）
  restoreLogin() {
    const token = storage.get('login_token', '')
    const user = storage.get('login_user', null)
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = {
        nickname: (user && user.nickname) || '',
        avatar: fixImage((user && user.avatar) || ''),
        createdAt: (user && user.createdAt) || 0
      }
    }
  },

  // 保存登录态到全局并持久化到本地（wx.setStorageSync）
  saveLogin(token, userInfo = {}) {
    if (!this.globalData.userInfo) {
      this.globalData.userInfo = { nickname: '', avatar: '', createdAt: 0 }
    }
    if (token) this.globalData.token = token
    if (userInfo) {
      if (userInfo.nickname !== undefined) this.globalData.userInfo.nickname = userInfo.nickname
      if (userInfo.avatar !== undefined) this.globalData.userInfo.avatar = userInfo.avatar
      if (userInfo.createdAt !== undefined) this.globalData.userInfo.createdAt = userInfo.createdAt
    }
    storage.set('login_token', this.globalData.token)
    storage.set('login_user', this.globalData.userInfo)
  },

  // 清除登录态（退出登录 / 登录失效时使用）
  clearLogin() {
    this.globalData.token = ''
    this.globalData.userInfo = { nickname: '', avatar: '', createdAt: 0 }
    storage.remove('login_token')
    storage.remove('login_user')
  },

  /**
   * 静默登录：wx.login 拿 code -> 后端换 openid 并签发 JWT -> 拉取资料。
   * 登录失败不阻断主流程（降级为未登录态，由页面引导授权）。
   */
  silentLogin() {
    wx.login({
      success: (res) => {
        if (!res.code) return
        api.login(res.code)
          .then((r) => {
            const token = r.token || ''  // 后端签发的 JWT，替代明文 openid
            const user = r.user || {}
            this.saveLogin(token, {
              nickname: user.nickname || '',
              avatar: fixImage(user.avatar || ''),
              createdAt: user.createdAt || 0
            })
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
