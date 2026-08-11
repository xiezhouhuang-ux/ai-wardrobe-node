<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api.js'
import { setTryOnResultData, clearTryOnResultData } from '../utils/tryon-cache.js'

const router = useRouter()

const users = ref([])
const step = ref('users')        // 'users' | 'wardrobe'
const currentUser = ref(null)    // 选中的用户 { openid, nickname, avatar }
const loadingUsers = ref(false)
const loadingWardrobe = ref(false)

const wardrobe = ref([])
const userPhoto = ref(null)
const selected = ref({})   // { 上衣: itemId, 下装: itemId, 鞋: itemId, 包: itemId }
const generating = ref(false)
const error = ref('')

const CATEGORIES = ['上衣', '下装', '鞋', '包']

// 按分类分组
const grouped = computed(() => {
  const map = {}
  for (const c of CATEGORIES) map[c] = []
  for (const it of wardrobe.value) {
    const cat = it.category
    if (map[cat]) map[cat].push(it)
    else {
      if (!map['其他']) map['其他'] = []
      map['其他'].push(it)
    }
  }
  return map
})

// 已选单品详情
const selectedItems = computed(() => {
  const arr = []
  for (const cat of CATEGORIES) {
    const id = selected.value[cat]
    if (!id) continue
    const it = wardrobe.value.find(i => i.id === id)
    if (it) arr.push(it)
  }
  return arr
})

const canGenerate = computed(() => {
  return selectedItems.value.length > 0 && !generating.value && !!userPhoto.value
})

onMounted(async () => {
  await loadUsers()
})

async function loadUsers() {
  loadingUsers.value = true
  error.value = ''
  try {
    const res = await api.getUsers()
    const list = res.items || res.list || res || []
    users.value = Array.isArray(list) ? list : []
  } catch (err) {
    error.value = err.message || '加载用户列表失败'
  } finally {
    loadingUsers.value = false
  }
}

async function enterWardrobe(user) {
  currentUser.value = user
  step.value = 'wardrobe'
  selected.value = {}
  clearTryOnResultData()
  loadingWardrobe.value = true
  error.value = ''
  try {
    const [items, photo] = await Promise.all([
      api.getItems(user.openid),
      api.getUserPhoto(),
    ])
    wardrobe.value = items || []
    userPhoto.value = photo || null
  } catch {
    userPhoto.value = null
  } finally {
    loadingWardrobe.value = false
  }
}

function backToUsers() {
  step.value = 'users'
  currentUser.value = null
  wardrobe.value = []
  userPhoto.value = null
  selected.value = {}
  clearTryOnResultData()
}

function toggleSelect(cat, itemId) {
  if (selected.value[cat] === itemId) {
    delete selected.value[cat]
  } else {
    selected.value[cat] = itemId
  }
  selected.value = { ...selected.value }
}

function isSelected(cat, itemId) {
  return selected.value[cat] === itemId
}

async function generate() {
  const ids = Object.values(selected.value).filter(Boolean)
  if (ids.length === 0) return
  generating.value = true
  error.value = ''
  try {
    const res = await api.tryOn(ids, currentUser.value.openid)
    setTryOnResultData({ resultUrl: res.resultUrl, itemIds: ids, targetOpenid: currentUser.value.openid })
    router.push('/tryon/result')
  } catch (err) {
    error.value = err.message || '试穿生成失败，请重试'
  } finally {
    generating.value = false
  }
}

function reset() {
  selected.value = {}
  error.value = ''
  clearTryOnResultData()
}
</script>

<template>
  <div class="page">
    <h1 class="title">🪄 AI 试穿</h1>

    <!-- 步骤一：选择用户 -->
    <div v-if="step === 'users'">
      <div class="sub">请选择一位用户，进入其衣橱进行试穿</div>
      <div v-if="loadingUsers" class="empty">加载用户列表中…</div>
      <div v-else-if="!users.length" class="empty">暂无用户</div>
      <div v-else class="user-list">
        <div
          v-for="u in users"
          :key="u.openid"
          class="user-row"
          @click="enterWardrobe(u)"
        >
          <img
            v-if="u.avatar"
            :src="u.avatar"
            class="user-avatar"
            alt="头像"
          />
          <div v-else class="user-avatar placeholder">{{ (u.nickname || u.openid || '?').slice(0, 1) }}</div>
          <div class="user-info">
            <div class="user-name">{{ u.nickname || '未命名用户' }}</div>
            <div class="user-openid">{{ u.openid }}</div>
          </div>
          <span class="enter">进入衣橱 ›</span>
        </div>
      </div>
    </div>

    <!-- 步骤二：选择单品试穿 -->
    <div v-else>
      <div class="crumb" @click="backToUsers">‹ 返回用户列表</div>
      <div class="user-bar">
        <img v-if="currentUser.avatar" :src="currentUser.avatar" class="bar-avatar" alt="头像" />
        <div v-else class="bar-avatar placeholder">{{ (currentUser.nickname || '?').slice(0, 1) }}</div>
        <div class="bar-info">
          <div class="bar-name">{{ currentUser.nickname || '未命名用户' }}</div>
          <div class="bar-openid">{{ currentUser.openid }}</div>
        </div>
      </div>

      <div v-if="loadingWardrobe" class="empty">加载衣橱中…</div>

      <template v-else>
        <!-- 无全身照 -->
        <div v-if="!userPhoto" class="banner">
          <span>⚠️ 该用户尚未上传全身正面照，无法生成试穿效果</span>
        </div>
        <div v-else class="photo-row">
          <img :src="userPhoto.url" class="user-photo" alt="全身照" />
          <span class="badge">✓ 底图已就绪</span>
        </div>

        <!-- 选择单品 -->
        <div class="section">
          <h3>选择穿搭单品 <span class="sel-count">已选 {{ selectedItems.length }} / 4</span></h3>
          <div v-for="cat in CATEGORIES" :key="cat" class="cat-section">
            <div class="cat-head">{{ cat }}</div>
            <div v-if="grouped[cat]?.length" class="items-row">
              <div
                v-for="it in grouped[cat]"
                :key="it.id"
                class="item-card"
                :class="{ active: isSelected(cat, it.id) }"
                @click="toggleSelect(cat, it.id)"
              >
                <div class="item-thumb" :style="{ backgroundImage: `url('${it.imageUrl || ''}')` }"></div>
                <div class="item-meta">
                  <span class="item-name">{{ it.color || it.category }}</span>
                  <span class="item-check">{{ isSelected(cat, it.id) ? '✓' : '' }}</span>
                </div>
              </div>
            </div>
            <div v-else class="cat-empty">暂无{{ cat }}单品</div>
          </div>
        </div>

        <!-- 已选概览 + 操作 -->
        <div v-if="selectedItems.length" class="overview">
          <div class="ov-title">已选单品</div>
          <div class="ov-items">
            <div v-for="it in selectedItems" :key="it.id" class="ov-chip">
              <div class="ov-thumb" :style="{ backgroundImage: `url('${it.imageUrl || ''}')` }"></div>
              <span>{{ it.category }} · {{ it.color }}</span>
            </div>
          </div>
          <button class="btn primary" :disabled="!canGenerate" @click="generate">
            {{ generating ? '正在生成…' : '生成试穿效果' }}
          </button>
          <button class="btn outline" style="margin-top:8px" @click="reset">🔄 重新选择</button>
        </div>
      </template>
    </div>

    <div v-if="error" class="error">⚠️ {{ error }}</div>
  </div>
</template>

<style scoped>
.page { padding: 0 4px 100px; }
.title { font-size: 22px; margin: 0 0 16px; }

/* 提示条 */
.banner {
  background: #fff7e6;
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 14px;
}
.btn.ghost {
  height: 30px;
  border: 1px solid var(--accent, #5b7fff);
  background: #fff;
  color: var(--accent, #5b7fff);
  border-radius: 7px;
  padding: 0 12px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}

/* 底图信息 */
.photo-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  background: #fff;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--line, #e8ecf1);
}
.user-photo {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  object-fit: cover;
}
.badge {
  color: #3a9d5a;
  font-size: 13px;
  font-weight: 500;
}

/* 选择区 */
.section {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid var(--line, #e8ecf1);
  margin-bottom: 14px;
}
.section h3 {
  margin: 0 0 12px;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sel-count { font-size: 12px; color: var(--muted, #93a0b2); font-weight: 400; }

.cat-section { margin-bottom: 12px; }
.cat-section:last-child { margin-bottom: 0; }
.cat-head {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink, #1a2b3c);
  margin-bottom: 8px;
}
.cat-empty {
  font-size: 12px;
  color: var(--muted, #93a0b2);
  padding: 8px 0;
}

.items-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  -webkit-overflow-scrolling: touch;
}
.items-row::-webkit-scrollbar { display: none; }

.item-card {
  flex-shrink: 0;
  width: 72px;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border .15s;
  background: #f8f9fb;
}
.item-card.active { border-color: var(--accent, #5b7fff); }
.item-thumb {
  width: 72px;
  height: 72px;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.item-meta {
  padding: 4px 6px 6px;
  font-size: 11px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-check { color: var(--accent, #5b7fff); font-weight: 700; flex-shrink: 0; }

/* 已选概览 */
.overview {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid var(--line, #e8ecf1);
  margin-bottom: 14px;
}
.ov-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; }
.ov-items { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.ov-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f0f2f6;
  border-radius: 8px;
  padding: 4px 10px 4px 4px;
  font-size: 12px;
}
.ov-thumb {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background-size: cover;
  background-position: center;
}

.btn.primary {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: var(--accent, #5b7fff);
  color: #fff;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
}
.btn.primary:disabled { opacity: .5; cursor: not-allowed; }

.btn.outline {
  width: 100%;
  height: 38px;
  border: 1px solid var(--line, #dde);
  background: #fff;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

.error {
  color: #e23b3b;
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
}

/* 步骤一：用户列表 */
.sub {
  font-size: 13px;
  color: var(--muted, #93a0b2);
  margin-bottom: 12px;
}
.empty {
  text-align: center;
  color: var(--muted, #93a0b2);
  font-size: 13px;
  padding: 30px 0;
}
.user-list {
  background: #fff;
  border-radius: 14px;
  border: 1px solid var(--line, #e8ecf1);
  overflow: hidden;
}
.user-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  cursor: pointer;
  transition: background .15s;
}
.user-row:hover { background: #f7f9fc; }
.user-row + .user-row { border-top: 1px solid var(--line, #eef1f5); }
.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  background: #eef1f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--muted, #93a0b2);
  font-weight: 600;
}
.user-info { flex: 1; min-width: 0; }
.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink, #1a2b3c);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-openid {
  font-size: 11px;
  color: var(--muted, #93a0b2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.enter { color: var(--accent, #5b7fff); font-size: 13px; flex-shrink: 0; }

/* 步骤二：头部 */
.crumb {
  font-size: 13px;
  color: var(--accent, #5b7fff);
  cursor: pointer;
  margin-bottom: 12px;
}
.user-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  border: 1px solid var(--line, #e8ecf1);
  border-radius: 12px;
  padding: 10px 14px;
  margin-bottom: 14px;
}
.bar-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  background: #eef1f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--muted, #93a0b2);
  font-weight: 600;
}
.bar-info { min-width: 0; }
.bar-name { font-size: 14px; font-weight: 600; color: var(--ink, #1a2b3c); }
.bar-openid { font-size: 11px; color: var(--muted, #93a0b2); }
</style>
