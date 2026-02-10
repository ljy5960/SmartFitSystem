<template>
  <div class="main-layout">
    <el-container>
      <el-header class="header">
        <div class="logo">
          <span class="icon">👗</span> SmartFit 智能适配系统
        </div>
        <div class="user-info">
          <el-button type="danger" plain size="small" @click="logout">退出登录</el-button>
        </div>
      </el-header>

      <el-main>
        <el-tabs v-model="activeTab" type="border-card" @tab-click="handleTabClick">

          <el-tab-pane label="📏 尺码预测" name="predict">
            <el-row :gutter="40">

              <el-col :xs="24" :sm="12">
                <div class="panel-title">1. 输入您的数据</div>
                <el-form :model="form" label-position="top" size="large">
                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="身高 (cm)">
                        <el-input-number v-model="form.height" :min="140" :max="220" style="width:100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="腰围 (cm)">
                        <el-input-number v-model="form.waist" :min="40" :max="150" style="width:100%" />
                        <div v-if="!form.waist" class="input-tip">* 请务必输入腰围数值</div>
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-row :gutter="20">
                    <el-col :span="12">
                      <el-form-item label="Bra 底围 (如 34, 36)">
                        <el-input-number v-model="form.bra_num" :min="28" :max="50" style="width:100%" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="12">
                      <el-form-item label="罩杯">
                        <el-select v-model="form.cup_size" placeholder="请选择" style="width:100%">
                          <el-option
                            v-for="item in cupOptions"
                            :key="item.value"
                            :label="item.label"
                            :value="item.value"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                  </el-row>

                  <el-divider content-position="left">商品详情</el-divider>

                  <el-form-item label="商品种类">
                    <el-radio-group v-model="form.category" @change="resetResult" fill="#409EFF">
                      <el-radio-button label="tops">上衣</el-radio-button>
                      <el-radio-button label="dresses">连衣裙</el-radio-button>
                      <el-radio-button label="bottoms">下装</el-radio-button>
                      <el-radio-button label="outerwear">外套</el-radio-button> </el-radio-group>
                  </el-form-item>

                  <el-form-item label="尝试尺码 (US Size)">
                    <div style="width: 100%; display: flex; align-items: center;">

                       <el-slider
                         v-model="form.size"
                         :min="0"
                         :max="26"
                         show-input
                         input-size="small"
                         style="flex: 1; margin-right: 10px;"
                       />

                       <el-tooltip content="点击查看尺码对照表" placement="top">
                         <el-button
                           circle
                           size="small"
                           type="info"
                           plain
                           :icon="QuestionFilled"
                           @click="showSizeChart = true"
                           style="flex-shrink: 0; border: none; font-size: 18px;"
                         />
                       </el-tooltip>
                    </div>
                  </el-form-item>

                  <el-button type="primary" size="large" @click="predict" :loading="loading" class="predict-btn">
                    立即分析合身度
                  </el-button>
                </el-form>
              </el-col>

              <el-col :xs="24" :sm="12">
                <div class="panel-title">2. 适配分析结果</div>
                <el-card shadow="hover" class="result-card">

                  <div class="image-container">
                    <el-image
                      :src="currentImage"
                      fit="cover"
                      style="width: 100%; height: 400px; border-radius: 8px;"
                    >
                      <template #placeholder>
                        <div class="image-slot">加载中...</div>
                      </template>
                      <template #error>
                        <div class="image-slot">
                          <i class="el-icon-picture-outline"></i>
                        </div>
                      </template>
                    </el-image>

                    <div v-if="result" class="result-overlay">
                      <div class="badge-container">
                         <el-tag :type="getResultTagType(result.result)" effect="dark" class="big-badge">
                           {{ result.result }}
                         </el-tag>
                      </div>
                      <div class="stats">
                        <div class="stat-item">
                          <span>置信度</span>
                          <span class="stat-val">{{ result.probs.fit }}%</span>
                        </div>
                        <el-progress
                          :percentage="parseFloat(result.probs.fit)"
                          :status="result.result.includes('Fit') || result.result.includes('合身') ? 'success' : 'warning'"
                          :stroke-width="10"
                        />
                        <div class="sub-stats">
                          <small>偏小: {{ result.probs.small }}%</small>
                          <small>偏大: {{ result.probs.large }}%</small>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="!result" class="placeholder-text">
                    👈 请在左侧输入数据并点击分析
                  </div>

                </el-card>
              </el-col>
            </el-row>
          </el-tab-pane>

          <el-tab-pane label="📜 历史记录" name="history">

            <div class="history-header">
              <span>共 {{ historyList.length }} 条记录</span>
              <el-button
                type="danger"
                size="small"
                plain
                @click="handleClearHistory"
                :disabled="historyList.length === 0"
              >
                🗑️ 清空记录
              </el-button>
            </div>

            <el-table
              :data="historyList"
              stripe
              style="width: 100%"
              v-loading="historyLoading"
              height="500"
            >
              <el-table-column prop="date" label="时间" width="160" />
              <el-table-column label="预览" width="80">
                <template #default="scope">
                  <el-image
                    :src="scope.row.image_url"
                    style="width: 40px; height: 40px; border-radius: 4px;"
                    fit="cover"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="category" label="种类">
                <template #default="scope">
                  {{ formatCategory(scope.row.category) }}
                </template>
              </el-table-column>
              <el-table-column prop="size" label="尺码" width="80" />
              <el-table-column prop="result" label="结果">
                <template #default="scope">
                  <el-tag :type="getResultTagType(scope.row.result)" size="small">
                    {{ scope.row.result }}
                  </el-tag>
                </template>
              </el-table-column>

              <el-table-column label="操作" width="120" fixed="right">
                <template #default="scope">
                  <el-button link type="primary" size="small" @click="handleViewDetail(scope.row)">
                    🔍 查看详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

        </el-tabs>
      </el-main>

      <el-dialog
        v-model="showSizeChart"
        title="📏 美国标准尺码对照表 (US Standard)"
        width="800px"
        center
        destroy-on-close
        align-center
      >
        <div style="text-align: center; max-height: 70vh; overflow-y: auto;">
          <el-image
            src="/chart.png"
            fit="contain"
            alt="Size Chart"
            style="width: 100%; height: auto;"
          >
             <template #placeholder>
               <div class="image-slot">加载图片中...</div>
             </template>
             <template #error>
               <div style="padding: 40px; color: #909399;">
                 ❌ 未找到 chart.png 图片，请检查 public 文件夹
               </div>
             </template>
          </el-image>
        </div>
      </el-dialog>
      <el-dialog
        v-model="detailsVisible"
        title="📜 历史记录详情"
        width="600px"
        center
        destroy-on-close
      >
        <div v-if="currentDetail" class="detail-layout">

          <div class="detail-left">
             <el-image :src="currentDetail.image_url" fit="cover" class="detail-img" />
             <div style="margin-top:15px; text-align:center;">
               <el-tag :type="getResultTagType(currentDetail.result)" effect="dark" size="large">
                 {{ currentDetail.result }}
               </el-tag>
               <p style="color:#666; font-size:12px; margin-top:5px;">
                 置信度: {{ currentDetail.confidence }}
               </p>
             </div>
          </div>

          <div class="detail-right">
             <el-divider content-position="left">商品参数</el-divider>
             <el-descriptions :column="1" border size="small">
               <el-descriptions-item label="预测时间">{{ currentDetail.date }}</el-descriptions-item>
               <el-descriptions-item label="商品种类">{{ formatCategory(currentDetail.category) }}</el-descriptions-item>
               <el-descriptions-item label="尝试尺码">
                 <span style="font-weight:bold;">US {{ currentDetail.size }}</span>
               </el-descriptions-item>
             </el-descriptions>

             <el-divider content-position="left">当时身体数据</el-divider>
             <el-descriptions :column="2" border size="small" v-if="currentDetail.body_data">
               <el-descriptions-item label="身高">{{ currentDetail.body_data.height }} cm</el-descriptions-item>
               <el-descriptions-item label="腰围">{{ currentDetail.body_data.waist }}</el-descriptions-item>
               <el-descriptions-item label="Bra 底围">{{ currentDetail.body_data.bra }}</el-descriptions-item>
               <el-descriptions-item label="罩杯">
                 {{ currentDetail.body_data.cup ? currentDetail.body_data.cup.toUpperCase() : '-' }}
               </el-descriptions-item>
               <el-descriptions-item label="臀围">{{ parseInt(currentDetail.body_data.hips) }}</el-descriptions-item>
             </el-descriptions>
             <div v-else style="color:#999; text-align:center; padding:10px;">
               (该记录暂无身体数据详情)
             </div>
          </div>
        </div>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="detailsVisible = false">关闭</el-button>
          </span>
        </template>
      </el-dialog>

    </el-container>
  </div>
</template>

<script setup>
// ✅ 修复：清理重复导入，添加 QuestionFilled 图标导入
import { reactive, ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'

// --- 状态定义 ---
const router = useRouter()
const loading = ref(false)
const historyLoading = ref(false)
const activeTab = ref('predict')
const result = ref(null)
const historyList = ref([])
const showSizeChart = ref(false) // 控制尺码表弹窗

// 详情弹窗
const detailsVisible = ref(false)
const currentDetail = ref(null)

// 罩杯选项
const cupOptions = [
  { label: 'A', value: 'a' },
  { label: 'B', value: 'b' },
  { label: 'C', value: 'c' },
  { label: 'D', value: 'd' },
  { label: 'DD/E', value: 'dd/e' },
  { label: 'F', value: 'f' },
  { label: 'G', value: 'g' },
  { label: 'H', value: 'h' }
]

// 默认图片映射
const defaultImages = {
  tops: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=600&q=80',
  dresses: 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=600&q=80',
  bottoms: 'https://images.unsplash.com/photo-1541099649105-f69ad21f3246?w=600&q=80',
  outerwear: 'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=600&q=80' // 👈 新增
}

// 表单数据
const form = reactive({
  height: 165,
  waist: 70,
  hips: 90,
  bra_num: 34,
  cup_size: 'b',
  category: 'dresses',
  size: 6
})

// --- 计算属性 ---
const currentImage = computed(() => {
  if (result.value && result.value.image_url) {
    return result.value.image_url
  }
  return defaultImages[form.category] || defaultImages.dresses
})

// --- 生命周期 ---
onMounted(() => {
  const token = localStorage.getItem('token')
  if (!token) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }

  const savedData = localStorage.getItem('userData')
  if (savedData) {
    try {
      const parsed = JSON.parse(savedData)
      if (parsed.height) form.height = parsed.height
      if (parsed.waist) form.waist = parsed.waist
      if (parsed.bra_num || parsed.bra) form.bra_num = parsed.bra_num || parsed.bra
      if (parsed.cup_size || parsed.cup) form.cup_size = parsed.cup_size || parsed.cup
    } catch (e) {
      console.error("解析用户数据失败", e)
    }
  }
  fetchHistory() // 初始化时加载历史记录
})

// --- 核心功能 ---

const resetResult = () => {
  result.value = null
}

const getAuthHeader = () => {
  const token = localStorage.getItem('token')
  return { Authorization: `Bearer ${token}` }
}

const predict = async () => {
  loading.value = true
  try {
    const res = await axios.post('http://localhost:5000/predict', form, {
      headers: getAuthHeader()
    })

    result.value = res.data
    ElMessage.success('分析完成！')

    // 更新本地存储
    localStorage.setItem('userData', JSON.stringify(form))
    // 预测成功后刷新历史记录列表
    fetchHistory()

  } catch (error) {
    if (error.response && error.response.status === 401) {
      ElMessage.error('登录已过期')
      logout()
    } else {
      ElMessage.error('预测失败: ' + (error.response?.data?.msg || '网络错误'))
    }
  } finally {
    loading.value = false
  }
}

const fetchHistory = async () => {
  historyLoading.value = true
  try {
    const res = await axios.get('http://localhost:5000/history', {
      headers: getAuthHeader()
    })
    historyList.value = res.data
  } catch (error) {
    if (error.response?.status === 401) logout()
  } finally {
    historyLoading.value = false
  }
}

// 清除历史记录
const handleClearHistory = () => {
  ElMessageBox.confirm(
    '确定要清空所有历史记录吗？此操作不可恢复。',
    '警告',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await axios.delete('http://localhost:5000/history', {
        headers: getAuthHeader()
      })
      ElMessage.success('历史记录已清空')
      historyList.value = []
    } catch (error) {
      ElMessage.error('清除失败')
    }
  }).catch(() => {})
}

// 查看详情
const handleViewDetail = (row) => {
  currentDetail.value = row
  detailsVisible.value = true
}

const handleTabClick = (tab) => {
  if (tab.props.name === 'history') {
    fetchHistory()
  }
}

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userData')
  router.push('/login')
}

// --- 辅助 UI 函数 ---

const getResultTagType = (resStr) => {
  if (!resStr) return 'info'
  if (resStr.includes('Fit') || resStr.includes('合身')) return 'success'
  if (resStr.includes('Small') || resStr.includes('偏小')) return 'warning'
  return 'danger'
}

const formatCategory = (cat) => {
  const map = {
    'tops': '上衣',
    'dresses': '连衣裙',
    'bottoms': '下装',
    'outerwear': '外套' // 👈 新增
  }
  return map[cat] || cat
}
</script>

<style scoped>
/* 页面布局 */
.main-layout {
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
  background-color: #fff;
  display: flex;
  flex-direction: column;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding: 0 20px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  z-index: 10;
}

.logo {
  font-size: 22px;
  font-weight: 700;
  color: #409EFF;
  display: flex;
  align-items: center;
}
.logo .icon { margin-right: 8px; }

/* 面板标题 */
.panel-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #303133;
  border-left: 5px solid #409EFF;
  padding-left: 12px;
}

.input-tip {
  font-size: 12px;
  color: #F56C6C;
  line-height: 1.2;
  margin-top: 4px;
}

/* 按钮样式 */
.predict-btn {
  width: 100%;
  margin-top: 20px;
  font-weight: bold;
  height: 45px;
  font-size: 16px;
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.3);
}

/* 布局优化：滑块与按钮 */
.slider-container {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%; /* 关键：必须占满宽度 */
}

.custom-slider {
  flex: 1; /* 关键：自动伸展 */
  width: auto; /* 防止宽度被锁死 */
}
.help-btn {
  flex-shrink: 0; /* 防止按钮被挤压 */
  font-size: 16px;
  border: none;
}

.help-btn {
  font-size: 16px;
  border: none;
}
.help-btn:hover {
  background-color: #ecf5ff;
}

/* 结果卡片 */
.result-card {
  border: none;
  background: #f8f9fa;
  position: relative;
  overflow: hidden;
}

.image-container {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 400px;
  background: #eef2f7;
  color: #909399;
  font-size: 16px;
}

/* 结果悬浮层 */
.result-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.95);
  padding: 20px;
  border-top: 1px solid #ebeef5;
  backdrop-filter: blur(5px);
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.badge-container { text-align: center; margin-bottom: 15px; }
.big-badge { font-size: 18px; padding: 8px 25px; height: auto; }
.stats { color: #606266; }
.stat-item { display: flex; justify-content: space-between; margin-bottom: 5px; font-weight: 500; }
.sub-stats { display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: #909399; }
.placeholder-text { text-align: center; color: #909399; padding: 40px; font-style: italic; }

/* 历史记录头部 */
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding: 0 5px;
  color: #909399;
  font-size: 14px;
}

/* 详情弹窗样式 */
.detail-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.detail-left {
  width: 40%;
  flex-shrink: 0;
}
.detail-right {
  flex-grow: 1;
}
.detail-img {
  width: 100%;
  height: 300px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* 移动端适配 */
@media (max-width: 600px) {
  .detail-layout {
    flex-direction: column;
  }
  .detail-left {
    width: 100%;
    margin-bottom: 20px;
  }
}
</style>