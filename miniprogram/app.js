// app.js
const fixImage = require('./utils/image.js')
const storage = require('./utils/storage.js')

App({
  globalData: {
    // 后端地址，开发期填你本机局域网 IP + 端口
    // 真机调试时不能填 localhost，必须是本机 IP
    // baseURL: 'https://wardrobe.maidane.com',
    // 注意：小程序运行在微信客户端，localhost 指向手机自身而非后端电脑，
    // 必须填后端电脑的局域网 IP（开发者工具/真机调试需勾选“不校验合法域名”）。
    baseURL: 'http://localhost:3020',
    userInfo: { nickname: '', avatar: '', createdAt: 0, openid: '' },
    token: '', // 登录令牌（JWT），请求时放在 Authorization 头
    pendingTryonItemId: '', // 从详情页跳 AI 搭配时，待自动选中的单品 id
    statusBarHeight: 20,
    windowWidth: 375
  },

  onLaunch() {
    // 系统信息：状态栏高度、屏幕宽度等
    try {
      const win = wx.getWindowInfo()
      this.globalData.statusBarHeight = win.statusBarHeight
      this.globalData.windowWidth = win.windowWidth
    } catch (e) {
      console.warn('getWindowInfo failed', e)
    }
    // 先尝试从本地恢复登录态（重启小程序后无需重新授权即可登录）
    this.restoreLogin()
    // 注意：不再自动静默登录。未登录时不会主动调用 /api/auth/login，
    // 也不自动跳转授权页；点击「微信授权登录」才发起登录请求。

    // 隐私保护指引适配：chooseAvatar / getPhoneNumber 等接口需用户先同意隐私协议。
    // 注册全局拦截，未授权时拉起系统隐私授权窗，用户同意后再继续原接口调用。
    this.setupPrivacy()
  },

  // 全局错误兜底：吞掉部分开发者工具/基础库下 chooseAvatar 原生组件误报的
  // "chooseAvatar:fail ... not found" 渲染层错误，避免弹窗打断（真实设备正常）。
  onError(err) {
    const msg = (err && (err.message || err)) + ''
    if (msg.indexOf('chooseAvatar:fail') !== -1) {
      console.warn('已忽略 chooseAvatar 组件兼容报错:', msg)
      return
    }
    console.error('[App onError]', err)
  },

  // 隐私协议全局适配（基础库 2.32.3+）
  setupPrivacy() {
    if (typeof wx.onNeedPrivacyAuthorize !== 'function') return
    wx.onNeedPrivacyAuthorize((resolve) => {
      if (typeof wx.requirePrivacyAuthorize !== 'function') {
        // 旧基础库不支持，直接放行
        resolve({ event: 'agree', errMsg: 'requirePrivacyAuthorize:ok' })
        return
      }
      wx.requirePrivacyAuthorize({
        success: () => resolve({ event: 'agree', errMsg: 'requirePrivacyAuthorize:ok' }),
        fail: () => resolve({ event: 'disagree' })
      })
    })
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
        createdAt: (user && user.createdAt) || 0,
        openid: (user && user.openid) || ''
      }
    }
  },

  // 保存登录态到全局并持久化到本地（wx.setStorageSync）
  saveLogin(token, userInfo = {}) {
    if (!this.globalData.userInfo) {
      this.globalData.userInfo = { nickname: '', avatar: '', createdAt: 0, openid: '' }
    }
    if (token) this.globalData.token = token
    console.log(userInfo)
    if (userInfo) {
      if (userInfo.nickname !== undefined) this.globalData.userInfo.nickname = userInfo.nickname
      if (userInfo.avatar !== undefined) this.globalData.userInfo.avatar = userInfo.avatar
      if (userInfo.createdAt !== undefined) this.globalData.userInfo.createdAt = userInfo.createdAt
      if (userInfo.openid !== undefined) this.globalData.userInfo.openid = userInfo.openid
    }
    storage.set('login_token', this.globalData.token)
    storage.set('login_user', this.globalData.userInfo)
  },

  // 便捷获取当前登录用户 openid（登录时已持久化，无需再调 /api/user/profile）
  getOpenid() {
    return (this.globalData.userInfo && this.globalData.userInfo.openid) || ''
  },

  // 清除登录态（退出登录 / 登录失效时使用）
  clearLogin() {
    this.globalData.token = ''
    this.globalData.userInfo = { nickname: '', avatar: '', createdAt: 0, openid: '' }
    storage.remove('login_token')
    storage.remove('login_user')
  }
})
