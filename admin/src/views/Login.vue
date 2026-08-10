<template>
  <div class="login">
    <div class="card">
      <h1 class="title">AI 衣橱 · 后台管理</h1>
      <p class="sub">管理员登录</p>
      <input v-model="username" class="input" placeholder="账号" @keyup.enter="onLogin" />
      <input v-model="password" type="password" class="input" placeholder="密码" @keyup.enter="onLogin" />
      <div v-if="error" class="err">{{ error }}</div>
      <button class="btn" :disabled="loading" @click="onLogin">
        {{ loading ? '登录中…' : '登 录' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '../api'

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const router = useRouter()

async function onLogin() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = '请输入账号和密码'
    return
  }
  loading.value = true
  try {
    const res = await adminApi.login(username.value.trim(), password.value)
    localStorage.setItem('admin_token', res.token)
    router.push('/dashboard')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1677ff 0%, #001529 100%);
}
.card {
  width: 360px;
  background: #fff;
  border-radius: 12px;
  padding: 36px 32px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}
.title {
  margin: 0;
  font-size: 20px;
  text-align: center;
}
.sub {
  margin: 6px 0 24px;
  text-align: center;
  color: var(--text-2);
}
.input {
  width: 100%;
  height: 42px;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0 14px;
  margin-bottom: 16px;
  font-size: 14px;
  outline: none;
}
.input:focus {
  border-color: var(--primary);
}
.err {
  color: #ff4d4f;
  font-size: 13px;
  margin-bottom: 12px;
}
.btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 6px;
  background: var(--primary);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
}
.btn:disabled {
  opacity: 0.6;
}
</style>
