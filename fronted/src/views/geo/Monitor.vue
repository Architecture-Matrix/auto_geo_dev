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

interface Record {
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
const records = ref<Record[]>([])
const stats = ref({
  total_keywords: 0,
  keyword_found: 0,
  company_found: 0,
  hit_rate: 0,
})

const projectsLoading = ref(false)
const recordsLoading = ref(false)
const checking = ref(false)

const currentRecord = ref<Record | null>(null)

// 对话框状态
const showAnswerDialog = ref(false)

// 检测表单
const checkForm = ref({
  projectId: null as number | null,
  keywordId: null as number | null,
  platforms: ['doubao', 'qianwen', 'deepseek'],
})

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
    const result = await indexCheckApi.check({
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
const viewAnswer = (record: Record) => {
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
const getPlatformType = (platform: string) => {
  const types: Record<string, string> = {
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
    const result = await reportsApi.getTrends(30)
    return result || []
  } catch (error) {
    console.error('加载趋势数据失败:', error)
    return []
  }
}

// 渲染图表
const renderChart = (data: any[]) => {
  if (!chartInstance) return

  const dates = data.map(d => d.date)
  const keywordFound = data.map(d => d.keyword_found_count)
  const companyFound = data.map(d => d.company_found_count)
  const totalChecks = data.map(d => d.total_checks)

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
      data: dates,
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
        data: keywordFound,
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
        data: companyFound,
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
        data: totalChecks,
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

// ==================== 生命周期 ====================
onMounted(async () => {
  await loadProjects()
  await loadRecords()
  await loadStats()
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
</style>
