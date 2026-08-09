// utils/nav.js —— 自定义导航栏（状态栏 + 胶囊高度适配）
function getStatusBarHeight() {
  try { return wx.getWindowInfo().statusBarHeight || 20 } catch (e) { return 20 }
}

// 右上角胶囊信息：top / height，开发者工具 2.27+ 支持
function getMenuRect() {
  try {
    const rect = wx.getMenuButtonBoundingClientRect()
    return rect || { top: 0, height: 24, right: 0, width: 87 }
  } catch (e) {
    return { top: 0, height: 24, right: 0, width: 87 }
  }
}

// 导航栏自身高度（状态栏以下）= 胶囊上下间距*2 + 胶囊高度
// 间距 = menuRect.top - statusBarHeight，标准公式
function getNavBarHeight() {
  const sb = getStatusBarHeight()
  const rect = getMenuRect()
  const gap = Math.max(rect.top - sb, 4)
  return gap * 2 + rect.height
}

module.exports = {
  getStatusBarHeight,
  getMenuRect,
  getNavBarHeight
}