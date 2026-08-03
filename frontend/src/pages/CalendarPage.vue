<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import * as api from '../api.js'

const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth())
const selectedDate = ref('')
const dayOutfit = ref(null)
const wardrobe = ref([])
const withOutfitDates = ref(new Set())
const saving = ref(false)
const error = ref('')
const pickerCat = ref('')

const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const SLOTS = [
  { cat: '上衣', key: 'top' },
  { cat: '下装', key: 'bottom' },
  { cat: '鞋', key: 'shoes' },
  { cat: '包', key: 'bag' },
]

const editing = ref({ top: null, bottom: null, shoes: null, bag: null, note: '' })

function pad(n) { return String(n).padStart(2, '0') }
function ymd(y, m, d) { return `${y}-${pad(m + 1)}-${pad(d)}` }

const firstWeekday = computed(() => new Date(year.value, month.value, 1).getDay())
const daysInMonth = computed(() => new Date(year.value, month.value + 1, 0).getDate())

const cells = computed(() => {
  const arr = []
  for (let i = 0; i < firstWeekday.value; i++) arr.push(null)
  for (let d = 1; d <= daysInMonth.value; d++) arr.push(d)
  return arr
})

const monthLabel = computed(() => `${year.value}年 ${['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'][month.value]}`)

function changeMonth(delta) {
  let m = month.value + delta
  let y = year.value
  if (m < 0) { m = 11; y-- }
  if (m > 11) { m = 0; y++ }
  year.value = y
  month.value = m
}

const todayStr = ymd(today.getFullYear(), today.getMonth(), today.getDate())

function selectDate(d) {
  if (!d) return
  selectedDate.value = ymd(year.value, month.value, d)
  loadDay(selectedDate.value)
}

// 当月所有穿搭数据
const outfitsForMonth = ref({})

// 获取某天的穿搭图片列表（用于日历格子展示）
function dayOutfitImages(dateStr) {
  const o = outfitsForMonth.value[dateStr]
  if (!o || !o.items) return []
  return o.items.map((it) => it.imageUrl)
}

async function loadOutfitsForMonth() {
  try {
    const all = await api.getOutfits()
    const m = `${year.value}-${pad(month.value + 1)}`
    const set = new Set()
    for (const o of all) {
      if (o.date && o.date.startsWith(m)) {
        set.add(o.date)
        outfitsForMonth.value[o.date] = o
      }
    }
    withOutfitDates.value = set
  } catch (e) { /* ignore */ }
}

async function loadDay(date) {
  error.value = ''
  try {
    const o = await api.getOutfits(date)
    dayOutfit.value = o
    const map = {}
    for (const it of (o.items || [])) map[it.category] = it
    editing.value = {
      top: map['上衣'] || null,
      bottom: map['下装'] || null,
      shoes: map['鞋'] || null,
      bag: map['包'] || null,
      note: o.note || '',
    }
  } catch (e) {
    dayOutfit.value = null
    editing.value = { top: null, bottom: null, shoes: null, bag: null, note: '' }
  }
}

function wardrobeByCat(cat) {
  return wardrobe.value.filter((it) => it.category === cat)
}

function openPicker(cat) { pickerCat.value = cat }
function pickItem(cat, it) {
  const slot = SLOTS.find((s) => s.cat === cat)
  if (slot) editing.value[slot.key] = { category: cat, itemId: it.id, imageUrl: it.imageUrl, name: `${cat}·${it.color || ''}` }
  pickerCat.value = ''
}
function clearSlot(key) { editing.value[key] = null }
function closeEditor() { selectedDate.value = '' }

const editingItems = computed(() => {
  const out = []
  for (const s of SLOTS) {
    const v = editing.value[s.key]
    if (v) out.push(v)
  }
  return out
})

async function save() {
  if (!selectedDate.value) return
  saving.value = true
  error.value = ''
  try {
    await api.saveOutfit(selectedDate.value, editingItems.value, editing.value.note)
    withOutfitDates.value = new Set([...withOutfitDates.value, selectedDate.value])
    outfitsForMonth.value[selectedDate.value] = { date: selectedDate.value, items: editingItems.value, note: editing.value.note }
    dayOutfit.value = { date: selectedDate.value, items: editingItems.value, note: editing.value.note }
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!selectedDate.value) return
  saving.value = true
  error.value = ''
  try {
    await api.deleteOutfit(selectedDate.value)
    const s = new Set(withOutfitDates.value)
    s.delete(selectedDate.value)
    withOutfitDates.value = s
    delete outfitsForMonth.value[selectedDate.value]
    dayOutfit.value = null
    editing.value = { top: null, bottom: null, shoes: null, bag: null, note: '' }
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

// 统计数据
const selectedDateLabel = computed(() => {
  // 安全格式化日期显示
  const s = selectedDate.value
  if (typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s)) return s
  if (typeof s === 'string' && s.includes('[object')) {
    // 尝试从 year/month 重构
    return ymd(year.value, month.value, today.getDate())
  }
  return String(s || '')
})

// 真实衣橱单品映射（id -> 单品），用于统计时取一致的名称与图片
const realMap = computed(() => {
  const m = {}
  for (const it of wardrobe.value || []) m[it.id] = it
  return m
})

// 取单品真实信息：优先衣橱，回退到穿搭记录里的值
function resolveItem(it) {
  const id = it.itemId || it.imageUrl
  const real = id ? realMap.value[id] : null
  return {
    id,
    imageUrl: (real && real.imageUrl) || it.imageUrl || '',
    name: (real && (real.color || real.name)) ? `${real.category || ''}·${real.color || ''}`.replace(/^·/, '') : (it.name || ''),
    category: (real && real.category) || it.category || '',
  }
}

const stats = computed(() => {
  const byDate = outfitsForMonth.value
  const all = Object.values(byDate)

  // 本月最常穿搭：统计每件单品在本月穿搭中出现的次数（按真实单品归并），取最高者
  const freq = {} // id -> { count, imageUrl, name, category }
  for (const o of all) {
    for (const it of (o.items || [])) {
      const r = resolveItem(it)
      if (!r.id) continue
      if (!freq[r.id]) freq[r.id] = { count: 0, imageUrl: r.imageUrl, name: r.name, category: r.category }
      freq[r.id].count++
    }
  }
  let topItem = null
  for (const id in freq) {
    if (!topItem || freq[id].count > topItem.count) topItem = { itemId: id, ...freq[id] }
  }
  const mostWorn = topItem
    ? { ...topItem, label: `${topItem.name}（${topItem.count} 次）` }
    : null

  // 连续穿搭：找某件单品连续出现（按日期）的最长天数
  let bestStreak = null
  for (const id in freq) {
    let streak = 0
    let last = null
    const dates = Object.keys(byDate).sort()
    for (const ds of dates) {
      const has = (byDate[ds].items || []).some(it => (it.itemId || it.imageUrl) === id)
      if (has) {
        if (last !== null) {
          const diff = dateDiffDays(last, ds)
          if (diff === 1) streak++
          else streak = 1
        } else streak = 1
        last = ds
      }
    }
    if (streak > 0 && (!bestStreak || streak > bestStreak.days)) {
      bestStreak = { itemId: id, days: streak, imageUrl: freq[id].imageUrl, name: freq[id].name }
    }
  }
  const streakItem = bestStreak
    ? { ...bestStreak, label: `${bestStreak.name}（连续 ${bestStreak.days} 天）` }
    : null

  return { mostWorn, streakItem, daysWithOutfit: all.length }
})

function dateDiffDays(a, b) {
  const da = new Date(a + 'T00:00:00')
  const db = new Date(b + 'T00:00:00')
  return Math.round((db - da) / 86400000)
}

onMounted(async () => {
  try { wardrobe.value = await api.getItems() } catch (e) { error.value = e.message }
  await loadOutfitsForMonth()
  selectDate(today.getDate())
})

watch([year, month], async () => { await loadOutfitsForMonth() })
</script>

<template>
  <div class="cal-page">
    <!-- 顶部标题栏 -->
    <div class="header">
      <h1>日历</h1>
    </div>

    <!-- 月份导航 -->
    <div class="month-nav">
      <button class="nav" @click="changeMonth(-1)">‹</button>
      <span class="month-label">{{ monthLabel }}</span>
      <button class="nav" @click="changeMonth(1)">›</button>
    </div>

    <!-- 星期头 -->
    <div class="week-row">
      <span v-for="w in WEEK" :key="w" class="wk">{{ w }}</span>
    </div>

    <!-- 日历网格 -->
    <div class="grid">
      <div
        v-for="(d, i) in cells"
        :key="i"
        class="cell"
        :class="{
          empty: !d,
          sel: d && selectedDate === ymd(year, month, d),
          today: d && todayStr === ymd(year, month, d),
          has: d && withOutfitDates.has(ymd(year, month, d)),
        }"
        @click="selectDate(d)"
      >
        <!-- 无穿搭：显示日期数字 -->
        <template v-if="d && !dayOutfitImages(ymd(year, month, d)).length">
          <span class="d">{{ d }}</span>
        </template>
        <!-- 有穿搭：显示单品透明抠图 -->
        <template v-else-if="d">
          <div class="outfit-preview">
            <img
              v-for="(u, ti) in dayOutfitImages(ymd(year, month, d))"
              :key="ti"
              :src="u"
              class="oi"
            />
          </div>
          <span class="d-overlay">{{ d }}</span>
        </template>
      </div>
    </div>

    <!-- 统计区 -->
    <div class="stats-bar">
      <div class="stat-item">
        <div
          class="stat-thumb"
          :style="stats.mostWorn ? { backgroundImage: `url('${stats.mostWorn.imageUrl}')` } : {}"
        >{{ stats.mostWorn ? '' : '👗' }}</div>
        <div class="stat-info">
          <span class="stat-val">本月最常穿搭</span>
          <span class="stat-sub">{{ stats.mostWorn ? stats.mostWorn.label : '暂无数据' }}</span>
        </div>
      </div>
      <div class="stat-item">
        <div
          class="stat-thumb"
          :style="stats.streakItem ? { backgroundImage: `url('${stats.streakItem.imageUrl}')` } : {}"
        >{{ stats.streakItem ? '' : '⭐' }}</div>
        <div class="stat-info">
          <span class="stat-val">连续穿搭</span>
          <span class="stat-sub">{{ stats.streakItem ? stats.streakItem.label : '暂无数据' }}</span>
        </div>
      </div>
    </div>

    <!-- 点击日期后弹出的编辑面板 -->
    <div v-if="selectedDate" class="editor-mask" @click.self="closeEditor">
      <div class="editor-sheet">
        <div class="ed-head">
          <h2>{{ selectedDateLabel }} 的穿搭</h2>
          <button class="x" @click="closeEditor">✕</button>
        </div>

        <div class="slots">
          <div v-for="s in SLOTS" :key="s.key" class="slot">
            <div class="slot-body" @click="openPicker(s.cat)">
              <template v-if="editing[s.key]">
                <div class="chosen">
                  <div class="thumb" :style="{ backgroundImage: `url('${editing[s.key].imageUrl}')` }"></div>
                  <div class="meta">
                    <div class="nm">{{ editing[s.key].name }}</div>
                    <button class="clr" @click.stop="clearSlot(s.key)">移除</button>
                  </div>
                </div>
              </template>
              <div v-else class="add">＋ 选择{{ s.cat }}</div>
            </div>
          </div>
        </div>

        <textarea
          v-model="editing.note"
          class="note"
          rows="2"
          placeholder="备注（可选）"
        ></textarea>

        <div class="ed-actions">
          <button v-if="dayOutfit" class="btn ghost" :disabled="saving" @click="remove">删除</button>
          <button class="btn primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : (dayOutfit ? '更新穿搭' : '保存穿搭') }}
          </button>
        </div>

        <div v-if="error" class="error">⚠️ {{ error }}</div>
      </div>
    </div>

    <!-- 单品选择面板 -->
    <div v-if="pickerCat" class="picker-mask" @click.self="pickerCat = ''">
      <div class="picker">
        <div class="picker-head">
          <span>选择{{ pickerCat }}</span>
          <button class="x" @click="pickerCat = ''">✕</button>
        </div>
        <div class="picker-list">
          <div
            v-for="it in wardrobeByCat(pickerCat)"
            :key="it.id"
            class="pick-item"
            @click="pickItem(pickerCat, it)"
          >
            <div class="thumb" :style="{ backgroundImage: `url('${it.imageUrl}')` }"></div>
            <span class="pi-name">{{ it.color }} {{ it.style }}</span>
          </div>
          <div v-if="wardrobeByCat(pickerCat).length === 0" class="pick-empty">
            衣橱里还没有{{ pickerCat }}单品
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cal-page {
  width: 100%;
  box-sizing: border-box;
  padding-bottom: 80px;
}

/* 顶部标题栏 */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 4px;
}
.header h1 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  flex: 1;
  text-align: center;
}
/* 月份导航 */
.month-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 10px 0 14px;
}
.month-label {
  font-size: 18px;
  font-weight: 600;
  min-width: 140px;
  text-align: center;
}
.nav {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--line);
  background: #fff;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 星期头 */
.week-row {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  margin-bottom: 2px;
}
.wk {
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  padding: 6px 0;
  font-weight: 500;
}

/* 日历网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  background: #f0f0f0;
  border-radius: 12px;
  overflow: hidden;
}
.cell {
  position: relative;
  aspect-ratio: 0.85;
  background: #fff;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  padding: 3px;
  cursor: pointer;
  min-height: 52px;
}
.cell.empty { background: transparent; cursor: default; }
.cell:not(.empty):active { background: #e8eaef; }
.cell.sel { box-shadow: inset 0 0 0 2px var(--accent); }
.cell.today .d { color: var(--accent); font-weight: 700; }

/* 日期数字 */
.d {
  font-size: 13px;
  line-height: 1;
  z-index: 2;
  position: relative;
}
.d-overlay {
  position: absolute;
  top: 3px;
  left: 3px;
  font-size: 11px;
  font-weight: 700;
  color: #333;
  text-shadow: 0 0 3px rgba(255,255,255,0.9);
  z-index: 2;
}

/* 有穿搭时的单品预览图（透明抠图直接填充） */
.outfit-preview {
  position: absolute;
  inset: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: center;
  gap: 1px;
  padding: 2px;
  overflow: hidden;
}
.oi {
  max-height: 100%;
  max-width: calc(50% - 1px);
  object-fit: contain;
  object-position: bottom center;
}

/* 底部统计区 */
.stats-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
  padding: 14px 16px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid var(--line);
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-thumb {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background-color: #f0f2f6;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.stat-info { display: flex; flex-direction: column; }
.stat-val { font-size: 14px; font-weight: 500; }
.stat-sub { font-size: 12px; color: var(--muted); }

/* 编辑器弹窗（点击日期后弹出） */
.editor-mask {
  position: fixed;
  inset: 0;
  background: rgba(20,30,60,.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 16px;
}
.editor-sheet {
  width: 100%;
  max-width: 460px;
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-sizing: border-box;
}
.ed-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.ed-head h2 { font-size: 17px; margin: 0; }
.x { border: none; background: none; font-size: 18px; cursor: pointer; color: var(--muted); }
.slots { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.slot-body {
  border: 1px dashed var(--line);
  border-radius: 12px;
  min-height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 10px;
}
.add { color: var(--muted); font-size: 13px; }
.chosen { display: flex; align-items: center; gap: 10px; width: 100%; }
.thumb {
  width: 52px;
  height: 52px;
  border-radius: 8px;
  background: #f0f2f6 center/contain no-repeat;
  flex: none;
}
.meta { display: flex; flex-direction: column; gap: 4px; }
.nm { font-size: 13px; }
.clr {
  align-self: flex-start;
  border: none;
  background: none;
  color: var(--accent);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.note {
  width: 100%;
  margin-top: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
  font-size: 13px;
  resize: vertical;
  box-sizing: border-box;
}
.ed-actions { margin-top: 12px; display: flex; gap: 10px; }
.btn {
  height: 42px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
}
.btn.primary {
  flex: 1;
  border: none;
  background: var(--accent);
  color: #fff;
}
.btn.primary:disabled { opacity: .6; }
.btn.ghost {
  width: 100px;
  border: 1px solid #f0bcbc;
  color: #e23b3b;
  background: #fff;
}
.error { color: #e23b3b; font-size: 13px; margin-top: 10px; }

/* 单品选择面板 */
.picker-mask {
  position: fixed;
  inset: 0;
  background: rgba(20,30,60,.4);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 60;
}
.picker {
  width: 100%;
  max-width: 560px;
  background: #fff;
  border-radius: 16px 16px 0 0;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
}
.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
  font-weight: 600;
}
.x { border: none; background: none; font-size: 16px; cursor: pointer; }
.picker-list {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding: 16px;
  overflow: auto;
}
.pick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.pick-item .thumb { width: 100%; aspect-ratio: 1; }
.pi-name { font-size: 12px; color: var(--muted); }
.pick-empty {
  grid-column: 1/-1;
  text-align: center;
  color: var(--muted);
  padding: 30px 0;
  font-size: 13px;
}

/* 手机适配 */
@media (max-width: 480px) {
  .cal-page { padding-bottom: 70px; }
  .header h1 { font-size: 17px; }
  .month-label { font-size: 17px; min-width: 120px; }
  .cell { aspect-ratio: 0.82; min-height: 48px; padding: 2px; }
  .d { font-size: 12px; }
  .d-overlay { font-size: 10px; top: 2px; left: 2px; }
  .wk { font-size: 12px; padding: 5px 0; }
  .stats-bar { padding: 12px; gap: 8px; }
  .editor-sheet { padding: 14px; border-radius: 14px; }
  .slots { grid-template-columns: 1fr; gap: 8px; }
  .slot-body { min-height: 80px; }
  .thumb { width: 46px; height: 46px; }
  .picker-list { grid-template-columns: repeat(3, 1fr); gap: 8px; padding: 12px; }
}
</style>
