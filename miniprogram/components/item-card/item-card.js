// components/item-card/item-card.js
const { categoryColors } = require('../../utils/constants.js')
const fixImage = require('../../utils/image.js')

Component({
  properties: {
    item: { type: Object, value: {} }
  },
  observers: {
    'item'(item) {
      if (!item) return
      const seasons = (item.season || '').split(/[、,\s]+/).filter(Boolean)
      const dotColor = categoryColors[item.category] || '#c96b4a'
      const image = fixImage(item.image || item.imageUrl || item.previewUrl || '')
      this.setData({ seasons, dotColor, image })
    }
  },
  methods: {
    onTap() {
      this.triggerEvent('cardtap', { item: this.data.item }, { bubbles: false, composed: false })
    }
  }
})