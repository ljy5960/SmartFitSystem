import { createRouter, createWebHistory } from 'vue-router'

// ==========================================
// 1. 导入你的页面组件
// (注意：这里假设你的首页叫 Home.vue，登录页叫 Login.vue，
// 如果你的文件名不一样，请在这里修改为你实际的文件名)
// ==========================================
import Home from '../views/HomeView.vue'
import Login from '../views/LoginView.vue'
import AdminDashboard from '../views/AdminDashboard.vue'

// ==========================================
// 2. 配置所有的路由规则 (全部放在这一个数组里)
// ==========================================
const routes = [
  // 首页 (普通用户预测页面)
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  // 登录页
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  // --- 新增：管理员后台页面 ---
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: AdminDashboard,
    meta: {
      requiresAuth: true,  // 标记：必须登录才能访问
      requiresAdmin: true  // 标记：必须是管理员才能访问
    }
  }
  // 如果你还有注册页 (Register.vue) 等其他页面，直接在这里继续往下加 {} 即可
]

// ==========================================
// 3. 创建路由实例 (全局唯一，解决之前报错的关键)
// ==========================================
const router = createRouter({
  history: createWebHistory(),
  routes
})

// ==========================================
// 4. 全局路由安全守卫 (拦截非法访问)
// ==========================================
router.beforeEach((to, from, next) => {
  // 从浏览器的 localStorage 获取凭证
  const token = localStorage.getItem('token')
  const isAdmin = localStorage.getItem('is_admin') === 'true' // localStorage存的是字符串，判断是否为 'true'

  if (to.meta.requiresAuth && !token) {
    // 试图访问需要登录的页面，但没有 token
    alert('请先登录系统！')
    next('/login') // 踢回登录页
  }
  else if (to.meta.requiresAdmin && !isAdmin) {
    // 试图访问管理员页面，但没有管理员权限
    alert('安全拦截：权限不足，仅限管理员访问该后台！')
    next('/') // 踢回首页
  }
  else {
    // 正常放行
    next()
  }
})

// ==========================================
// 5. 导出路由实例
// ==========================================
export default router