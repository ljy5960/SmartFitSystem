<template>
  <div class="admin-dashboard">
    <div class="header">
      <h2>SmartFit 智能尺码推荐系统 - 管理后台</h2>
      <el-button type="danger" @click="handleLogout" plain>退出登录</el-button>
    </div>

    <div class="stats-cards">
      <div class="card">
        <h3>全站注册用户数</h3>
        <p class="number">{{ totalUsers }}</p>
      </div>
    </div>

        <div class="content-grid">
      <div class="chart-container">
        <h3>系统整体预测结果分布</h3>
        <div ref="pieChartRef" style="width: 100%; height: 400px;"></div>
      </div>

      <div class="user-table-container">
        <div class="title-row">
          <h3>用户列表管理</h3>
          <el-button type="primary" plain @click="fetchUsers">刷新列表</el-button>
        </div>

        <el-table :data="users" border stripe style="width: 100%">
          <el-table-column prop="id" label="用户ID" width="100" />
          <el-table-column prop="username" label="用户名" min-width="180" />
          <el-table-column label="身份" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.is_admin ? 'warning' : 'success'">
                {{ scope.row.is_admin ? '管理员' : '普通用户' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="history_count" label="预测记录数" width="130" />
          <el-table-column label="操作" width="160">
            <template #default="scope">
              <el-popconfirm
                title="确认删除该用户及其所有相关数据吗？"
                confirm-button-text="确认删除"
                cancel-button-text="取消"
                @confirm="handleDeleteUser(scope.row)"
              >
                <template #reference>
                  <el-button
                    type="danger"
                    size="small"
                    :disabled="scope.row.id === adminId || scope.row.is_admin"
                  >
                    删除
                  </el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const totalUsers = ref(0)
const pieChartRef = ref(null)
const router = useRouter()
const users = ref([])
const adminId = ref(null)
let chartInstance = null

const getAuthHeaders = () => {
  const token = localStorage.getItem('token')
  return { Authorization: `Bearer ${token}` }
}


const handleLogout = () => {
  // 1. 清除浏览器本地存储的所有鉴权和用户信息
  localStorage.removeItem('token')
  localStorage.removeItem('userData')
  localStorage.removeItem('is_admin')

  // 2. 提示用户
  ElMessage.success('已安全退出登录')

  // 3. 跳转回登录页
  router.push('/login')
}

// ==============================
// 获取后台统计数据 (保持不变)
// ==============================
const fetchDashboardData = async () => {
  try {

    // 请替换为您实际的后端地址和端口
    const response = await axios.get('http://127.0.0.1:5000/api/admin/dashboard/stats', {
      headers: getAuthHeaders()
    })

    if (response.data.code === 200) {
      totalUsers.value = response.data.data.total_users
      adminId.value = response.data.data.admin_id
      await nextTick()
      renderPieChart(response.data.data.prediction_distribution)
    } else {
      ElMessage.error(response.data.msg || '加载统计数据失败')
      router.push('/login')
    }
  } catch (error) {
    console.error('请求统计数据失败', error)
    if (error.response && error.response.status === 403) {
      ElMessage.error('安全拦截：您不是管理员，无法访问此页面！')
      router.push('/login')
      return
    }
    ElMessage.error('统计数据加载失败，请稍后重试')
  }
}

const fetchUsers = async () => {
  try {
    const response = await axios.get('http://127.0.0.1:5000/api/admin/users', {
      headers: getAuthHeaders()
    })

    if (response.data.code === 200) {
      users.value = response.data.data.users
    } else {
      ElMessage.error(response.data.msg || '获取用户列表失败')
    }
    } catch (error) {
    console.error('请求用户列表失败', error)
    ElMessage.error('用户列表加载失败，请稍后重试')
  }
}
const handleDeleteUser = async (user) => {
  try {
    const response = await axios.delete(`http://127.0.0.1:5000/api/admin/users/${user.id}`, {
      headers: getAuthHeaders()
    })

    if (response.data.code === 200) {
      ElMessage.success(`用户 ${user.username} 删除成功`)
      await Promise.all([fetchDashboardData(), fetchUsers()])
    } else {
      ElMessage.error(response.data.msg || '删除用户失败')
    }
  } catch (error) {
    console.error('删除用户失败', error)
    ElMessage.error(error.response?.data?.msg || '删除用户失败')
  }
}

// 渲染 ECharts 饼图 (保持不变)
const renderPieChart = (chartData) => {
  if (!pieChartRef.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(pieChartRef.value)
  const option = {
    tooltip: { trigger: 'item' },
    legend: { top: '5%', left: 'center' },
    series: [
      {
        name: '预测结果 (次)',
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {c}次 ({d}%)'
        },
        // 如果系统刚刚初始化，还没有任何预测记录，给个默认空数据
        data: chartData.length > 0 ? chartData : [{ value: 0, name: '暂无预测流水' }]
      }
    ]
  }
 chartInstance.setOption(option)
}

onMounted(async () => {
  await Promise.all([fetchDashboardData(), fetchUsers()])
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.admin-dashboard {
  padding: 30px;
  background-color: #f5f7fa;
  min-height: 100vh;
}

/* --- 新增：导航栏样式 --- */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  background: white;
  padding: 15px 30px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.header h2 {
  margin: 0;
  color: #333;
}
/* ----------------------- */

.stats-cards {
  display: flex;
  margin-bottom: 30px;
}
.card {
  background: white;
  padding: 20px 40px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
  text-align: center;
}
.card .number {
  font-size: 40px;
  color: #409EFF;
  font-weight: bold;
  margin: 10px 0;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

.chart-container,
.user-table-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}
.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.title-row h3,
.chart-container h3 {
  margin: 0;
}
</style>