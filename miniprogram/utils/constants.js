// utils/constants.js —— 静态字典（与后端识别品类保持一致）
const categories = ['上衣', '下装', '鞋', '包']
const colors = ['黑', '白', '灰', '米', '蓝', '绿', '红', '粉', '黄', '棕', '条纹', '格纹', '印花']
const styles = ['休闲', '街头', '复古', '通勤', '甜美', '运动', '极简']
const seasons = ['春', '夏', '秋', '冬']

// 单品分类图标颜色
const categoryColors = {
  '上衣': '#c96b4a',
  '下装': '#7a9b8e',
  '鞋': '#b88a9d',
  '包': '#8a8a9b'
}

module.exports = {
  categories,
  colors,
  styles,
  seasons,
  categoryColors
}