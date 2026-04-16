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
// 🟢 修改点：删除了未使用的 'computed'
import { ref, reactive } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const isRegister = ref(false)
const loading = ref(false)
const ruleFormRef = ref(null)
const form = reactive({ username: '', password: '' })

// --- 自定义验证逻辑 (保持不变，只是不再显示在输入框里) ---

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
        const res = await axios.post(`http://localhost:5000${endpoint}`, form)

        // ✅ 修改后的代码
if (!isRegister.value) {
  localStorage.setItem('token', res.data.token)
  localStorage.setItem('userData', JSON.stringify(res.data.user))

  // 1. 将后端返回的管理员状态存入 localStorage (存为字符串 'true' 或 'false')
  localStorage.setItem('is_admin', res.data.is_admin ? 'true' : 'false')

  ElMessage.success('登录成功')

  // 2. 根据权限判断跳转的页面
  if (res.data.is_admin) {
    router.push('/admin') // 管理员直接跳转到数据面板
  } else {
    router.push('/')      // 普通用户跳转到尺码推荐首页
  }
} else {
  ElMessage.success('注册成功，请登录')
  toggleMode()
}
      } catch (err) {
        ElMessage.error(err.response?.data?.msg || '请求失败')
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
  /* --- 修改点：使用本地背景图 --- */
  /* 确保您的图片路径正确，这里假设图片在 src/assets/images/login-bg.jpg */
  background-image: url('@/assets/images/login-bg.jpg');
  /* 让图片充满屏幕并保持比例 */
  background-size: cover;
  /* 图片居中 */
  background-position: center;
  /* 不重复 */
  background-repeat: no-repeat;
}

.box-card {
  width: 400px;
  /* 额外美化：设置卡片背景为半透明白色，并添加毛玻璃效果 */
  background-color: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border: none; /* 可选：去掉边框使融合感更强 */
}
</style>