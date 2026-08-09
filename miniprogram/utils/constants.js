// utils/constants.js —— 静态字典
// 注：颜色/风格/季节已由 VL 模型自动识别并直接以文本展示（可手动修改），
// 不再使用预设字典，故此处仅保留品类枚举与配色。
const categories = ['上衣', '下装', '鞋', '包']

// 单品分类图标颜色
const categoryColors = {
  '上衣': '#c96b4a',
  '下装': '#7a9b8e',
  '鞋': '#b88a9d',
  '包': '#8a8a9b'
}

module.exports = {
  categories,
  categoryColors
}