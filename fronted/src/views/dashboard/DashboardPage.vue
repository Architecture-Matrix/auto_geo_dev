<template>
  <div class="dashboard-page">
    <!-- 核心指标卡片 -->
    <div class="stats-cards">
      <div class="stat-card blue">
        <div class="stat-icon"><el-icon><Document /></el-icon></div>
        <div class="stat-content">
          <div class="stat-label">文章总数</div>
          <div class="stat-value">{{ stats.total_articles }}</div>
          <div class="stat-desc">累计生成</div>
        </div>
      </div>
      <div class="stat-card green">
        <div class="stat-icon"><el-icon><CircleCheck /></el-icon></div>
        <div class="stat-content">
          <div class="stat-label">已发布</div>
          <div class="stat-value">{{ stats.published_count }}</div>
          <div class="stat-desc">发布率 {{ publishRate }}%</div>
        </div>
      </div>
      <div class="stat-card purple">
        <div class="stat-icon"><el-icon><TrendCharts /></el-icon></div>
        <div class="stat-content">
          <div class="stat-label">AI收录数</div>
          <div class="stat-value">{{ stats.indexed_count }}</div>
          <div class="stat-desc">收录率 {{ stats.index_rate }}%</div>
        </div>
      </div>
      <div class="stat-card orange">
        <div class="stat-icon"><el-icon><Folder /></el-icon></div>
        <div class="stat-content">
          <div class="stat-label">活跃项目</div>
          <div class="stat-value">{{ overview.total_projects }}</div>
          <div class="stat-desc">正在运行</div>
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 左侧：SEO转化漏斗 -->
      <div class="chart-box">
        <h3 class="chart-title">SEO 转化漏斗</h3>
        <div ref="funnelChartRef" class="chart"></div>
      </div>

      <!-- 右侧：平台分布 -->
      <div class="chart-box">
        <h3 class="chart-title">平台收录分布</h3>
        <div ref="pieChartRef" class="chart"></div>
      </div>
    </div>

    <!-- 底部：收录趋势 -->
    <div class="chart-box full-width">
      <h3 class="chart-title">近7天收录趋势</h3>
      <div ref="lineChartRef" class="chart"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue'
import { Document, CircleCheck, TrendCharts, Folder } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import axios from 'axios'

// 状态定义
const stats = ref({
  total_articles: 0,
  published_count: 0,
  indexed_count: 0,
  index_rate: 0,
  platform_distribution: {}
})

const overview = ref({
  total_projects: 0
})

const publishRate = computed(() => {
  if (stats.value.total_articles === 0) return 0
  return ((stats.value.published_count / stats.value.total_articles) * 100).toFixed(1)
})

// 图表 DOM 引用
const funnelChartRef = ref(null)
const pieChartRef = ref(null)
const lineChartRef = ref(null)

// 加载数据
const loadData = async () => {
  try {
    // 1. 获取文章统计
    const res1 = await axios.get('http://127.0.0.1:8001/api/reports/article-stats')
    stats.value = res1.data

    // 2. 获取概览
    const res2 = await axios.get('http://127.0.0.1:8001/api/reports/overview')
    overview.value = res2.data

    // 初始化图表
    initFunnelChart()
    initPieChart()
    initLineChart()
  } catch (error) {
    console.error('加载数据失败', error)
  }
}

// 漏斗图
const initFunnelChart = () => {
  const chart = echarts.init(funnelChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        name: 'SEO转化',
        type: 'funnel',
        left: '10%',
        width: '80%',
        label: { formatter: '{b}: {c}' },
        data: [
          { value: stats.value.total_articles, name: '生成文章' },
          { value: stats.value.published_count, name: '已发布' },
          { value: stats.value.indexed_count, name: '已收录' }
        ]
      }
    ]
  })
}

// 饼图
const initPieChart = () => {
  const chart = echarts.init(pieChartRef.value)
  const data = Object.entries(stats.value.platform_distribution).map(([k, v]) => ({ value: v, name: k }))

  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center' },
    series: [
      {
        name: '发布平台',
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 10 },
        data: data.length ? data : [{ value: 0, name: '暂无数据' }]
      }
    ]
  })
}

// 折线图
const initLineChart = () => {
  const chart = echarts.init(lineChartRef.value)
  // 获取最近7天的日期
  const days = []
  const values = []
  for (let i = 6; i >= 0; i--) {
    const date = new Date()
    date.setDate(date.getDate() - i)
    days.push(`${date.getMonth() + 1}/${date.getDate()}`)
  }
  // 模拟趋势数据
  values.push(8, 12, 10, 15, 20, 25, stats.value.indexed_count || 30)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: days },
    yAxis: { type: 'value' },
    series: [
      {
        data: values,
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.2 },
        itemStyle: { color: '#6366f1' }
      }
    ]
  })
}

onMounted(() => {
  nextTick(() => {
    loadData()
  })

  // 监听窗口变化
  window.addEventListener('resize', () => {
    if (funnelChartRef.value) echarts.dispose(funnelChartRef.value)
    if (pieChartRef.value) echarts.dispose(pieChartRef.value)
    if (lineChartRef.value) echarts.dispose(lineChartRef.value)
    initFunnelChart()
    initPieChart()
    initLineChart()
  })
})
</script>

<style scoped lang="scss">
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

// 统计卡片
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;

  .stat-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
    background: var(--bg-secondary);
    border-radius: 12px;
    border: 1px solid var(--border);

    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      color: white;
    }

    &.blue .stat-icon { background: linear-gradient(135deg, #4a90e2, #357abd); }
    &.green .stat-icon { background: linear-gradient(135deg, #4caf50, #3d8b40); }
    &.purple .stat-icon { background: linear-gradient(135deg, #9c27b0, #7b1fa2); }
    &.orange .stat-icon { background: linear-gradient(135deg, #ff9800, #f57c00); }

    .stat-content {
      .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
        margin-bottom: 4px;
      }

      .stat-desc {
        font-size: 12px;
        color: var(--text-secondary);
      }
    }
  }
}

// 图表容器
.charts-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.chart-box {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--border);

  .chart-title {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 16px 0;
    color: var(--text-primary);
  }

  .chart {
    height: 300px;
    width: 100%;
  }

  &.full-width {
    width: 100%;
  }
}
</style>
