<template>
  <div class="login-container">
    <el-card class="box-card">
      <h2 style="text-align:center">{{ isRegister ? '注册账号' : '登录系统' }}</h2>
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="form.password" type="password" /></el-form-item>
        <el-button type="primary" @click="handleAuth" style="width:100%">{{ isRegister ? '注册' : '登录' }}</el-button>
        <div style="text-align:center; margin-top:10px">
          <el-link type="primary" @click="isRegister = !isRegister">{{ isRegister ? '去登录' : '去注册' }}</el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const isRegister = ref(false)
const form = reactive({ username: '', password: '' })

const handleAuth = async () => {
  const endpoint = isRegister.value ? '/register' : '/login'
  try {
    const res = await axios.post(`http://localhost:5000${endpoint}`, form)
    if (!isRegister.value) {
      localStorage.setItem('token', res.data.token)
      localStorage.setItem('userData', JSON.stringify(res.data.user))
      ElMessage.success('登录成功')
      router.push('/')
    } else {
      ElMessage.success('注册成功，请登录')
      isRegister.value = false
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || '请求失败')
  }
}
</script>
<style scoped>
.login-container { display: flex; justify-content: center; align-items: center; height: 100vh; background: #f0f2f5; }
.box-card { width: 380px; }
</style>