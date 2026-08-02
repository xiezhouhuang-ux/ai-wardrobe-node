// 识别会话：在上传→确认→预览各步骤间共享数据（避免刷新丢失）。
import { reactive } from 'vue'

export const session = reactive({
  photoId: null,
  photoUrl: null,
  candidates: [],   // VL 分析出的候选单品
  segmented: [],    // 分割后生成的单品卡片（含 imageUrl 预览图）
})

export function resetSession() {
  session.photoId = null
  session.photoUrl = null
  session.candidates = []
  session.segmented = []
}
