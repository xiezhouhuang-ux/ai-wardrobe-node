// 共享常量：分类中文标签、颜色取色等。

export const CATEGORY_LABELS = {
  Top: '上衣',
  Bottom: '下装',
  Shoes: '鞋',
  Bag: '包',
}

export const COLOR_HEX = {
  黑: '#222',
  白: '#fff',
  灰: '#9aa0a8',
  米: '#efe7d6',
  卡其: '#c3ad84',
  蓝: '#4a6fd0',
  牛仔蓝: '#3a5d9c',
  红: '#e23b3b',
  绿: '#3fae6b',
  棕: '#8a5a32',
  粉: '#f3a6c0',
  紫: '#9d6bff',
  黄: '#f2c531',
  橙: '#ef8b3b',
  银: '#cfd3da',
  金: '#d4af37',
  其他: '#b9bec7',
  未知: '#b9bec7',
}

export function colorHex(c) {
  return COLOR_HEX[c] || '#b9bec7'
}

export function catLabel(category) {
  return CATEGORY_LABELS[category] || category
}

// 抠图方式的中文说明
export function segmentMethodLabel(method) {
  switch (method) {
    case 'qwen-image':
      return 'Qwen 图像模型（原图分割）'
    case 'rembg-cutout':
      return '离线抠图（rembg）'
    case 'crop-fallback':
      return '裁剪（降级）'
    case 'demo-original':
    default:
      return '原图（未分割）'
  }
}
