<template>
  <div class="monitor-page">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card stat-blue">
        <div class="stat-value">{{ stats.total_keywords || 0 }}</div>
        <div class="stat-label">检测关键词</div>
      </div>
      <div class="stat-card stat-green">
        <div class="stat-value">{{ stats.keyword_found || 0 }}</div>
        <div class="stat-label">关键词命中</div>
      </div>
      <div class="stat-card stat-orange">
        <div class="stat-value">{{ stats.company_found || 0 }}</div>
        <div class="stat-label">公司名命中</div>
      </div>
      <div class="stat-card stat-purple">
        <div class="stat-value">{{ stats.hit_rate || 0 }}%</div>
        <div class="stat-label">总体命中率</div>
      </div>
    </div>

    <!-- 平台授权状态 -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">AI平台授权状态</h2>
        <el-button @click="refreshPlatformStatuses">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
      </div>
      
      <div v-loading="platformStatusesLoading" class="platform-status-list">
        <div 
          v-for="platform in platformStatuses" 
          :key="platform.id"
          class="platform-status-card"
          :class="platform.status"
        >
          <div class="platform-icon" :style="{ backgroundColor: platform.color + '20' }">
            <span :style="{ color: platform.color }">{{ platform.name.charAt(0) }}</span>
          </div>
          <div class="platform-info">
            <h4>{{ platform.name }}</h4>
            <p>{{ platform.url }}</p>
            <div class="status-info">
              <el-tag :type="getStatusType(platform.status)">
                {{ getStatusText(platform.status) }}
              </el-tag>
              <div v-if="platform.age_info && (platform.age_info.created_at || platform.age_info.last_modified)" class="age-info">
                上次授权: {{ formatDate(platform.age_info.created_at || platform.age_info.last_modified) }}
              </div>
            </div>
          </div>
          <div class="platform-actions">
            <el-button 
              type="primary"
              size="small"
              @click="startPlatformAuthFlow(platform.id)"
            >
              开启新的授权
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 检测操作区 -->
    <div class="section">
      <h2 class="section-title">收录检测</h2>
      <el-form :inline="true" :model="checkForm" class="check-form">
        <el-form-item label="选择项目">
          <el-select
            v-model="checkForm.projectId"
            placeholder="请选择项目"
            style="width: 200px"
            @change="onProjectChange"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="选择关键词">
          <el-select
            v-model="checkForm.keywordId"
            placeholder="请选择关键词"
            style="width: 200px"
            :disabled="!checkForm.projectId"
          >
            <el-option
              v-for="keyword in currentKeywords"
              :key="keyword.id"
              :label="keyword.keyword"
              :value="keyword.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="检测平台">
          <el-select v-model="checkForm.platforms" multiple style="width: 250px">
            <el-option label="豆包" value="doubao" />
            <el-option label="通义千问" value="qianwen" />
            <el-option label="DeepSeek" value="deepseek" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="checking"
            :disabled="!checkForm.keywordId"
            @click="runCheck"
          >
            <el-icon><Search /></el-icon>
            开始检测
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 检测结果表格 -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">检测记录</h2>
        <el-button @click="loadRecords">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <el-table
        v-loading="recordsLoading"
        :data="records"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="question" label="检测问题" min-width="250" show-overflow-tooltip />
        <el-table-column prop="platform" label="平台" width="120">
          <template #default="{ row }">
            <el-tag :type="getPlatformType(row.platform)">
              {{ getPlatformName(row.platform) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关键词命中" width="120">
          <template #default="{ row }">
            <el-tag :type="row.keyword_found ? 'success' : 'danger'">
              {{ row.keyword_found ? '命中' : '未命中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="公司名命中" width="120">
          <template #default="{ row }">
            <el-tag :type="row.company_found ? 'success' : 'danger'">
              {{ row.company_found ? '命中' : '未命中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="check_time" label="检测时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.check_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewAnswer(row)">
              查看回答
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 命中率趋势图表 -->
    <div class="section">
      <h2 class="section-title">命中率趋势</h2>
      <div ref="chartRef" class="chart-container" />
    </div>

    <!-- 回答详情对话框 -->
    <el-dialog
      v-model="showAnswerDialog"
      title="AI回答内容"
      width="600px"
    >
      <div v-if="currentRecord" class="answer-content">
        <div class="answer-question">
          <strong>检测问题：</strong>{{ currentRecord.question }}
        </div>
        <div class="answer-body">
          <strong>AI回答：</strong>
          <p>{{ currentRecord.answer || '（无回答内容）' }}</p>
        </div>
        <div class="answer-result">
          <el-tag :type="currentRecord.keyword_found ? 'success' : 'danger'">
            关键词：{{ currentRecord.keyword_found ? '命中' : '未命中' }}
          </el-tag>
          <el-tag :type="currentRecord.company_found ? 'success' : 'danger'">
            公司名：{{ currentRecord.company_found ? '命中' : '未命中' }}
          </el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAnswerDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Search,
  Refresh,
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { geoKeywordApi, indexCheckApi, reportsApi } from '@/services/api'
import { get, post } from '@/services/api'

// ==================== 类型定义 ====================
interface Project {
  id: number
  name: string
  company_name: string
}

interface Keyword {
  id: number
  keyword: string
}

interface CheckRecord {
  id: number
  keyword_id: number
  platform: string
  question: string
  answer?: string
  keyword_found?: boolean
  company_found?: boolean
  check_time: string
}

// ==================== 状态 ====================
const projects = ref<Project[]>([])
const keywords = ref<Keyword[]>([])
const records = ref<CheckRecord[]>([])
const stats = ref({
  total_keywords: 0,
  keyword_found: 0,
  company_found: 0,
  hit_rate: 0,
})

const recordsLoading = ref(false)
const checking = ref(false)

const currentRecord = ref<CheckRecord | null>(null)

// 对话框状态
const showAnswerDialog = ref(false)

// 检测表单
const checkForm = ref({
  projectId: null as number | null,
  keywordId: null as number | null,
  platforms: ['doubao', 'qianwen', 'deepseek'],
})

// 平台授权状态相关
interface Platform {
  id: string
  name: string
  url: string
  color: string
  status?: string
  age_info?: any
}

const platformStatuses = ref<Platform[]>([])
const platformStatusesLoading = ref(false)
const availablePlatforms = ref<Platform[]>([
  { id: 'doubao', name: '豆包', url: 'https://www.doubao.com', color: '#0066FF' },
  { id: 'deepseek', name: '深度求索', url: 'https://chat.deepseek.com', color: '#4D6BFE' },
  { id: 'qianwen', name: '通义千问', url: 'https://qianwen.com', color: '#FF6A00' }
])

// 图表相关
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// ==================== 计算属性 ====================
const currentKeywords = computed(() =>
  keywords.value.filter(k => k.keyword)
)

// ==================== 方法 ====================

// 加载项目列表
const loadProjects = async () => {
  try {
    const result = await geoKeywordApi.getProjects()
    projects.value = result || []
  } catch (error) {
    console.error('加载项目失败:', error)
  }
}

// 项目变化时加载关键词
const onProjectChange = async () => {
  checkForm.value.keywordId = null
  if (checkForm.value.projectId) {
    try {
      const result = await geoKeywordApi.getProjectKeywords(checkForm.value.projectId)
      keywords.value = result || []
    } catch (error) {
      console.error('加载关键词失败:', error)
    }
  }
}

// 加载检测记录
const loadRecords = async () => {
  recordsLoading.value = true
  try {
    const result = await indexCheckApi.getRecords({ limit: 100 })
    records.value = result || []
  } catch (error) {
    console.error('加载记录失败:', error)
  } finally {
    recordsLoading.value = false
  }
}

// 加载统计数据
const loadStats = async () => {
  try {
    const result = await reportsApi.getOverview()
    stats.value = {
      total_keywords: result.total_keywords || 0,
      keyword_found: result.keyword_found || 0,
      company_found: result.company_found || 0,
      hit_rate: result.overall_hit_rate || 0,
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 执行检测
const runCheck = async () => {
  if (!checkForm.value.keywordId) {
    ElMessage.warning('请选择关键词')
    return
  }

  const project = projects.value.find(p => p.id === checkForm.value.projectId)
  if (!project) {
    ElMessage.warning('请选择项目')
    return
  }

  if (!checkForm.value.platforms || checkForm.value.platforms.length === 0) {
    ElMessage.warning('请选择至少一个检测平台')
    return
  }

  checking.value = true
  try {
    const result = await indexCheckApi.checkKeyword({
      keyword_id: checkForm.value.keywordId,
      company_name: project.company_name,
      platforms: checkForm.value.platforms,
    })

    if (result.success) {
      await loadRecords()
      await loadStats()
      await loadTrendChart()
      ElMessage.success(result.message || '检测完成')
    } else {
      ElMessage.error(result.message || '检测失败')
    }
  } catch (error) {
    console.error('检测失败:', error)
    ElMessage.error('检测失败')
  } finally {
    checking.value = false
  }
}

// 查看回答
const viewAnswer = (record: CheckRecord) => {
  currentRecord.value = record
  showAnswerDialog.value = true
}

// 获取平台名称
const getPlatformName = (platform: string) => {
  const names: Record<string, string> = {
    doubao: '豆包',
    qianwen: '通义千问',
    deepseek: 'DeepSeek',
  }
  return names[platform] || platform
}

// 获取平台标签类型
const getPlatformType = (platform: string): 'success' | 'primary' | 'warning' | 'info' | 'danger' => {
  const types: Record<string, 'success' | 'primary' | 'warning' | 'info'> = {
    doubao: 'primary',
    qianwen: 'warning',
    deepseek: 'success',
  }
  return types[platform] || 'info'
}

// 格式化日期
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 初始化图表
const initChart = async () => {
  await nextTick()
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)

  // 加载趋势数据
  const trendData = await loadTrendData()
  renderChart(trendData)
}

// 加载趋势数据
const loadTrendData = async () => {
  try {
    const result = await reportsApi.getIndexTrend({ days: 30 })
    return result || []
  } catch (error) {
    console.error('加载趋势数据失败:', error)
    return []
  }
}

// 渲染图表
const renderChart = (data: any[]) => {
  if (!chartInstance) return

  // 处理空数据
  const safeData = Array.isArray(data) ? data : []
  
  const dates = safeData.map(d => d.date || '')
  const keywordFound = safeData.map(d => d.keyword_found_count || 0)
  const companyFound = safeData.map(d => d.company_found_count || 0)
  const totalChecks = safeData.map(d => d.total_checks || 0)

  const option = {
    tooltip: {
      trigger: 'axis',
    },
    legend: {
      data: ['关键词命中', '公司名命中', '总检测数'],
      textStyle: {
        color: 'var(--text-secondary)',
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates.length > 0 ? dates : ['无数据'],
      axisLabel: {
        color: 'var(--text-secondary)',
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: 'var(--text-secondary)',
      },
    },
    series: [
      {
        name: '关键词命中',
        type: 'line',
        data: keywordFound.length > 0 ? keywordFound : [0],
        smooth: true,
        itemStyle: { color: '#67c23a' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
            { offset: 1, color: 'rgba(103, 194, 58, 0.05)' },
          ]),
        },
      },
      {
        name: '公司名命中',
        type: 'line',
        data: companyFound.length > 0 ? companyFound : [0],
        smooth: true,
        itemStyle: { color: '#409eff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' },
          ]),
        },
      },
      {
        name: '总检测数',
        type: 'line',
        data: totalChecks.length > 0 ? totalChecks : [0],
        smooth: true,
        itemStyle: { color: '#e6a23c' },
      },
    ],
  }

  chartInstance.setOption(option)
}

// 加载并刷新图表
const loadTrendChart = async () => {
  const trendData = await loadTrendData()
  renderChart(trendData)
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

// ==================== 平台授权状态相关方法 ====================

// 加载平台授权状态
const loadPlatformStatuses = async () => {
  // 总是显示加载状态，确保用户知道正在刷新
  platformStatusesLoading.value = true
  
  try {
    // 这里应该从当前登录用户获取user_id，从路由参数或store获取project_id
    // 暂时使用固定值，实际应用中需要从上下文中获取
    const user_id = 1 // 示例值
    const project_id = 1 // 示例值

    // 构建基本平台状态列表，使用默认状态
    const initialStatuses = availablePlatforms.value.map(platform => ({
      ...platform,
      status: 'invalid',
      age_info: null
    }))
    
    // 立即显示初始状态，减少用户等待时间
    if (platformStatuses.value.length === 0) {
      platformStatuses.value = initialStatuses
    }

    // 并行执行所有请求，提高效率
    const [_, ...statusResponses] = await Promise.all([
      // 获取所有会话状态
      get('/auth/sessions', { user_id, project_id }, { 
        headers: { 'Cache-Control': 'no-cache' } 
      }).catch((err: any) => {
        console.error('获取会话列表失败:', err)
        return { success: false, data: { sessions: [] } }
      }),
      // 并行获取每个平台的状态
      ...availablePlatforms.value.map(platform => 
        get('/auth/session/status', {
          user_id,
          project_id,
          platform: platform.id
        }, {
          headers: { 'Cache-Control': 'no-cache' }
        }).catch((err: any) => {
          console.error(`获取${platform.name}状态失败:`, err)
          return { success: false, data: { status: 'invalid' } }
        })
      )
    ])

    // 更新平台状态
    const updatedStatuses = availablePlatforms.value.map((platform, index) => {
      let status = 'invalid'
      let age_info = null

      // 从平台状态响应中获取更详细的状态（优先使用这个，因为包含心跳检测结果）
      const statusResponse = statusResponses[index]
      if (statusResponse.success && statusResponse.data) {
        status = statusResponse.data.status
        age_info = statusResponse.data.age_info
      }

      return {
        ...platform,
        status,
        age_info
      }
    })

    platformStatuses.value = updatedStatuses
  } catch (err: any) {
    console.error('加载平台状态失败:', err)
    // 出错时不显示错误提示，避免影响用户体验
  } finally {
    platformStatusesLoading.value = false
  }
}

// 刷新平台授权状态
const refreshPlatformStatuses = () => {
  loadPlatformStatuses()
}

// 开始平台授权流程
const startPlatformAuthFlow = async (platformId: string) => {
  try {
    // 这里应该从当前登录用户获取user_id，从路由参数或store获取project_id
    // 暂时使用固定值，实际应用中需要从上下文中获取
    const user_id = 1 // 示例值
    const project_id = 1 // 示例值

    // 开始授权流程，只授权指定平台
    const platforms = [platformId]
    
    // 调用后端API开始授权流程
    const response = await post('/auth/start-flow', {
      user_id,
      project_id,
      platforms
    })

    if (response.success) {
      const authSessionId = response.auth_session_id
      
      if (authSessionId) {
        const platformName = availablePlatforms.value.find(p => p.id === platformId)?.name
        ElMessage.success(`${platformName}平台授权流程已开始，请检查浏览器弹出的窗口`)
        
        // 开始该平台的授权
        await startSinglePlatformAuth(authSessionId, platformId)
      } else {
        ElMessage.error('开始授权流程失败：未返回授权会话ID')
      }
    } else {
      ElMessage.error(response.error || '开始授权流程失败')
    }
  } catch (err: any) {
    ElMessage.error(`请求失败: ${err.message || '未知错误'}`)
  }
}

// 开始单个平台的授权
const startSinglePlatformAuth = async (authSessionId: string, platform: string) => {
  try {
    // 调用后端API开始单个平台的授权
    const response = await post(`/auth/start-platform/${authSessionId}`, {}, {
      params: { platform }
    })

    if (response.success) {
      // 后端现在直接打开授权窗口，不需要前端打开窗口
      ElMessage.success(`授权窗口已打开，请完成登录操作`)
      
      // 不自动检查授权状态，让用户手动刷新
      // 这样可以避免浏览器窗口被过早关闭
      
      // 但在授权流程结束后，提示用户刷新状态
      setTimeout(() => {
        ElMessage.info('授权完成后请点击"刷新状态"按钮获取最新授权状态')
      }, 10000) // 10秒后提示
    } else {
      ElMessage.error(response.error || '开始平台授权失败')
    }
  } catch (err: any) {
    ElMessage.error(`请求失败: ${err.message || '未知错误'}`)
  }
}



// 获取状态文本
const getStatusText = (status: string | undefined) => {
  const statusMap: Record<string, string> = {
    'valid': '已授权',
    'expiring': '已授权', // 即将过期也视为已授权
    'invalid': '未授权',
    'error': '错误'
  }
  return statusMap[status || ''] || '未知'
}

// 获取状态标签类型
const getStatusType = (status: string | undefined): 'success' | 'primary' | 'warning' | 'info' | 'danger' => {
  const typeMap: Record<string, 'success' | 'primary' | 'warning' | 'info' | 'danger'> = {
    'valid': 'success',
    'expiring': 'success', // 即将过期也使用成功标签
    'invalid': 'danger',
    'error': 'danger'
  }
  return typeMap[status || ''] || 'info'
}



// ==================== 生命周期 ====================
onMounted(async () => {
  await loadProjects()
  await loadRecords()
  await loadStats()
  await loadPlatformStatuses()
  await initChart()

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped lang="scss">
.monitor-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// 统计卡片
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  border-radius: 16px;
  padding: 24px;
  color: white;

  &.stat-blue {
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  }

  &.stat-green {
    background: linear-gradient(135deg, #4caf50 0%, #3d8b40 100%);
  }

  &.stat-orange {
    background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
  }

  &.stat-purple {
    background: linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%);
  }

  .stat-value {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .stat-label {
    font-size: 14px;
    opacity: 0.9;
  }
}

.section {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 24px;

  .section-title {
    margin: 0 0 16px 0;
    font-size: 16px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
}

.check-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.answer-content {
  display: flex;
  flex-direction: column;
  gap: 16px;

  .answer-question {
    padding: 12px;
    background: var(--bg-tertiary);
    border-radius: 8px;
  }

  .answer-body {
    strong {
      display: block;
      margin-bottom: 8px;
    }

    p {
      margin: 0;
      line-height: 1.8;
      color: var(--text-primary);
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  .answer-result {
    display: flex;
    gap: 12px;
  }
}

:deep(.el-table) {
  background: transparent;
  color: var(--text-primary);

  .el-table__header {
    th {
      background: var(--bg-tertiary);
      color: var(--text-secondary);
    }
  }

  .el-table__body {
    tr {
      background: transparent;

      &:hover td {
        background: var(--bg-tertiary);
      }
    }

    td {
      border-color: var(--border);
    }
  }
}

/* 平台授权状态样式 */
.platform-status-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.platform-status-card {
  display: flex;
  align-items: flex-start;
  padding: 20px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  transition: all 0.3s ease;
  background: var(--bg-secondary);
}

.platform-status-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.platform-status-card.valid {
  border-color: #28a745;
  background-color: #f8fff9;
}

.platform-status-card.expiring {
  border-color: #ffc107;
  background-color: #fffbf0;
}

.platform-status-card.invalid {
  border-color: #dc3545;
  background-color: #fff8f8;
}

.platform-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  flex-shrink: 0;
}

.platform-icon span {
  font-size: 20px;
  font-weight: 600;
}

.platform-info {
  flex: 1;
  min-width: 0;
}

.platform-info h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.platform-info p {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.age-info {
  font-size: 12px;
  color: var(--text-secondary);
}

.platform-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .platform-status-list {
    grid-template-columns: 1fr;
  }

  .platform-status-card {
    flex-direction: column;
    align-items: flex-start;
  }

  .platform-icon {
    margin-bottom: 12px;
  }

  .platform-info {
    margin-bottom: 16px;
  }

  .platform-actions {
    width: 100%;
    flex-direction: row;
  }

  .platform-actions .el-button {
    flex: 1;
  }
}
</style>
