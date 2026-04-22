<template>
  <div class="login-container">
    <el-card class="box-card">
      <h2 style="text-align:center">{{ isRegister ? '注册账号' : '登录系统' }}</h2>

      <el-form
        ref="ruleFormRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        status-icon
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleAuth" :loading="loading" style="width:100%">
            {{ isRegister ? '注册' : '登录' }}
          </el-button>
        </el-form-item>

        <div style="text-align:center; margin-top:10px">
          <el-link type="primary" @click="toggleMode">
            {{ isRegister ? '已有账号？去登录' : '没有账号？去注册' }}
          </el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import request from '@/utils/request' // 使用封装好的 request
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const isRegister = ref(false)
const loading = ref(false)
const ruleFormRef = ref(null)
const form = reactive({ username: '', password: '' })

// --- 自定义验证逻辑 ---

const validateUser = (rule, value, callback) => {
  if (!value) {
    return callback(new Error('请输入用户名'))
  }
  if (!isRegister.value) return callback()

  if (/\s/.test(value)) {
    return callback(new Error('账号不能包含空格'))
  }
  if (value.length < 6 || value.length > 12) {
    return callback(new Error('账号长度需在 6-12 位之间'))
  }
  if (/^\d+$/.test(value)) {
    return callback(new Error('账号不能全为数字'))
  }
  callback()
}

const validatePass = (rule, value, callback) => {
  if (!value) {
    return callback(new Error('请输入密码'))
  }
  if (!isRegister.value) return callback()

  if (/\s/.test(value)) {
    return callback(new Error('密码不能包含空格'))
  }
  if (/^\d+$/.test(value)) {
    return callback(new Error('密码不能为纯数字'))
  }
  if (!/^[A-Za-z0-9]+$/.test(value)) {
    return callback(new Error('密码只能包含字母和数字'))
  }
  const hasLetter = /[a-zA-Z]/.test(value)
  const hasDigit = /\d/.test(value)
  if (!hasLetter || !hasDigit) {
    return callback(new Error('密码必须包含数字和字母'))
  }

  callback()
}

const rules = reactive({
  username: [{ validator: validateUser, trigger: 'blur' }],
  password: [{ validator: validatePass, trigger: 'blur' }]
})

// --- 业务逻辑 ---

const toggleMode = () => {
  isRegister.value = !isRegister.value
  if (ruleFormRef.value) {
    ruleFormRef.value.resetFields()
  }
}

const handleAuth = () => {
  if (!ruleFormRef.value) return

  ruleFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      const endpoint = isRegister.value ? '/register' : '/login'
      try {
        // ✅ 核心修改点：这里使用导入的 request 替代 axios，并且去掉了硬编码的 http 地址
        const res = await request.post(endpoint, form)

        if (!isRegister.value) {
          // 这里如果是拦截器封装好的情况，可能 res 直接就是 data。
          // 如果你的 request.js 里返回的是 response，那么就需要 res.data.token
          // 如果这里报错，把 res.data 统一改成 res 即可，具体看 utils/request.js 的响应拦截器怎么写的。
          const responseData = res.data || res

          localStorage.setItem('token', responseData.token)
          localStorage.setItem('userData', JSON.stringify(responseData.user))
          localStorage.setItem('is_admin', responseData.is_admin ? 'true' : 'false')

          ElMessage.success('登录成功')

          if (responseData.is_admin) {
            router.push('/admin') // 管理员直接跳转到数据面板
          } else {
            router.push('/')      // 普通用户跳转到尺码推荐首页
          }
        } else {
          ElMessage.success('注册成功，请登录')
          toggleMode()
        }
      } catch (err) {
        // 防止出现 err.response 导致报错的兜底
        ElMessage.error(err.response?.data?.msg || err.message || '请求失败')
      } finally {
        loading.value = false
      }
    } else {
      ElMessage.warning('请检查输入格式')
      return false
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  /* 确保您的图片路径正确，这里假设图片在 src/assets/images/login-bg.jpg */
  background-image: url('@/assets/images/login-bg.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.box-card {
  width: 400px;
  background-color: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border: none;
}
</style>