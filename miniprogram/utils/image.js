// 统一图片地址处理：拼接 baseURL，并兼容本地临时/临时授权地址
function fixImage(u) {
  if (!u) return ''
  // 已是完整可显示地址：http(s)、微信本地临时文件、base64
  if (
    u.startsWith('http://') ||
    u.startsWith('https://') ||
    u.startsWith('wxfile://') ||
    u.startsWith('data:')
  ) {
    return u
  }
  // 绝对路径（/ 开头）或相对路径，统一拼接后端 baseURL
  const base = (getApp().globalData && getApp().globalData.baseURL) || ''
  return base + u
}

module.exports = fixImage
