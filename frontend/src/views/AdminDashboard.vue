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

    <div class="chart-container">
      <h3>系统整体预测结果分布</h3>
      <div ref="pieChartRef" style="width: 100%; height: 400px;"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus' // 新增：引入消息提示

const totalUsers = ref(0)
const pieChartRef = ref(null)
const router = useRouter()

// ==============================
// 新增：退出登录逻辑
// ==============================
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
    const token = localStorage.getItem('token')

    // 请替换为您实际的后端地址和端口
    const response = await axios.get('http://127.0.0.1:5000/api/admin/dashboard/stats', {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      totalUsers.value = response.data.data.total_users
      renderPieChart(response.data.data.prediction_distribution)
    } else {
      ElMessage.error(response.data.msg)
      router.push('/login')
    }
  } catch (error) {
    console.error("请求失败", error)
    if (error.response && error.response.status === 403) {
      ElMessage.error("安全拦截：您不是管理员，无法访问此页面！")
      router.push('/login')
    }
  }
}

// 渲染 ECharts 饼图 (保持不变)
const renderPieChart = (chartData) => {
  const myChart = echarts.init(pieChartRef.value)
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
  myChart.setOption(option)
}

onMounted(() => {
  fetchDashboardData()
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
.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}
</style>