<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api.js'
import { session } from '../session.js'
import { catLabel } from '../constants.js'

const router = useRouter()
const loading = ref(false)
const error = ref('')
// 每件单品处理状态：idle | pending | done
const status = ref([])
const overall = ref(0)

// 候选单品勾选状态（按索引），默认全选
const selected = ref([])

onMounted(() => {
  if (!session.photoUrl || !session.candidates.length) {
    // 直接访问本页且无数据时，回退到上传页
    router.replace('/upload')
    return
  }
  selected.value = session.candidates.map(() => true)
  status.value = session.candidates.map(() => 'idle')
})

const allChecked = computed({
  get: () => selected.value.length > 0 && selected.value.every(Boolean),
  set: (v) => { selected.value = selected.value.map(() => v) },
})

const chosenCount = computed(() => selected.value.filter(Boolean).length)

const candidatesView = computed(() =>
  session.candidates.map((c, i) => ({ ...c, _idx: i, _on: selected.value[i], _status: status.value[i] }))
)

async function goSegment() {
  const items = session.candidates.filter((_, i) => selected.value[i])
  if (!items.length) {
    error.value = '请至少勾选一个单品'
    return
  }
  error.value = ''
  loading.value = true
  overall.value = 0
  const chosenIdx = session.candidates
    .map((_, i) => i)
    .filter((i) => selected.value[i])
  const segmented = []
  try {
    for (let k = 0; k < chosenIdx.length; k++) {
      const i = chosenIdx[k]
      status.value[i] = 'pending'
      overall.value = Math.round((k / chosenIdx.length) * 100)
      // 每次只上传一件单品进行分割
      const seg = await api.segmentOne(session.photoUrl, session.candidates[i])
      segmented.push({ ...session.candidates[i], ...seg })
      status.value[i] = 'done'
      overall.value = Math.round(((k + 1) / chosenIdx.length) * 100)
    }
    session.segmented = segmented
    router.push('/preview')
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="confirm-wrap" v-if="session.photoUrl">
    <div class="section-head">
      <h2>确认识别结果</h2>
      <span class="count-hint">已选 {{ chosenCount }} / {{ session.candidates.length }}</span>
    </div>

    <div class="layout">
      <div class="photo-box">
        <img :src="session.photoUrl" alt="原图" />
        <span class="tag">原图</span>
      </div>

      <div class="list-box">
        <label class="select-all">
          <input type="checkbox" v-model="allChecked" />
          全选
        </label>

        <div v-if="session.candidates.length === 0" class="empty">
          视觉模型未识别到单品，请返回重新上传。
        </div>

        <div
          v-for="c in candidatesView"
          :key="c._idx"
          class="candidate"
          :class="{ off: !c._on, 'row-done': c._status === 'done' }"
          @click="!loading && (selected[c._idx] = !selected[c._idx])"
        >
          <input type="checkbox" :checked="c._on" :disabled="loading" @click.stop="selected[c._idx] = !selected[c._idx]" />
          <div class="meta">
            <div class="row1">
              <b>{{ catLabel(c.category) }}</b>
              <span>{{ c.color }}</span>
            </div>
            <div class="row2">{{ c.style }} · {{ c.season }} · {{ c.material }}</div>
          </div>
          <span v-if="c._status === 'pending'" class="spinner"></span>
          <span v-else-if="c._status === 'done'" class="cell-done">✓</span>
        </div>

        <div v-if="error" class="error">⚠️ {{ error }}</div>

        <div v-if="loading" class="proc-bar">
          <div class="proc-track"><div class="proc-fill" :style="{ width: overall + '%' }"></div></div>
          <div class="proc-text">正在分割单品… {{ overall }}%</div>
        </div>

        <div class="actions">
          <button class="btn ghost" :disabled="loading" @click="router.push('/upload')">重新上传</button>
          <button class="btn primary" :disabled="loading || chosenCount === 0" @click="goSegment">
            {{ loading ? '分割中…' : '确认并分割单品' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-wrap { max-width: 980px; margin: 0 auto; }
.layout { display: flex; gap: 20px; flex-wrap: wrap; }
.photo-box { position: relative; width: 320px; flex: none; }
.photo-box img { width: 100%; border-radius: 14px; border: 1px solid var(--line); }
.photo-box .tag {
  position: absolute; top: 10px; left: 10px; background: rgba(29,31,36,.7);
  color: #fff; font-size: 12px; padding: 3px 8px; border-radius: 999px;
}
.list-box { flex: 1; min-width: 280px; }
.select-all { display: inline-flex; align-items: center; gap: 6px; font-size: 14px; margin-bottom: 10px; }
.candidate {
  display: flex; align-items: center; gap: 10px;
  background: #fff; border: 1px solid var(--line); border-radius: 12px;
  padding: 12px 14px; margin-bottom: 10px; cursor: pointer; transition: .15s;
}
.candidate.off { opacity: .5; }
.candidate:hover { border-color: var(--accent); }
.candidate.row-done { border-color: #2bb673; }
.meta { flex: 1; }
.row1 { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.row2 { font-size: 12px; color: var(--muted); margin-top: 4px; }
.spinner {
  width: 16px; height: 16px; border-radius: 50%;
  border: 2px solid var(--line); border-top-color: var(--accent);
  animation: spin .7s linear infinite; flex: none;
}
.cell-done { color: #2bb673; font-weight: 700; flex: none; }
@keyframes spin { to { transform: rotate(360deg); } }
.actions { display: flex; gap: 10px; margin-top: 14px; }
.btn { height: 42px; border-radius: 10px; padding: 0 18px; font-size: 14px; cursor: pointer; border: 1px solid var(--line); background: #fff; }
.btn.primary { background: var(--accent); color: #fff; border: none; flex: 1; }
.btn.primary:disabled { opacity: .5; cursor: not-allowed; }
.btn.ghost:disabled { opacity: .5; cursor: not-allowed; }
.error { color: #e23b3b; font-size: 13px; margin-top: 8px; }
.proc-bar { margin-top: 14px; }
.proc-track { height: 8px; border-radius: 999px; background: var(--line); overflow: hidden; }
.proc-fill { height: 100%; background: var(--accent); transition: width .3s; }
.proc-text { font-size: 12px; color: var(--muted); margin-top: 6px; }
</style>
