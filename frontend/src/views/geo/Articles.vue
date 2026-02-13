<template>
  <div class="articles-page">
    <!-- 选择区域 -->
    <div class="section">
      <h2 class="section-title">生成文章</h2>
      <el-form :inline="true" :model="generateForm" class="generate-form">
        <el-form-item label="选择项目">
          <el-select
            v-model="generateForm.projectId"
            placeholder="请选择项目"
            style="width: 180px"
            @change="onProjectChange"
          >
            <el-option
              v-for="project in validProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择关键词">
          <el-select
            v-model="generateForm.keywordId"
            placeholder="请选择关键词"
            style="width: 180px"
            :disabled="!generateForm.projectId"
          >
            <el-option
              v-for="keyword in keywords"
              :key="keyword.id"
              :label="keyword.keyword || keyword.name"
              :value="keyword.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="发布平台">
          <el-select
            v-model="generateForm.targetPlatforms"
            placeholder="请选择发布平台"
            multiple
            style="width: 220px"
            clearable
          >
            <el-option
              v-for="platform in PLATFORM_OPTIONS"
              :key="platform.value"
              :label="platform.label"
              :value="platform.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="发布策略">
          <el-radio-group v-model="generateForm.publishStrategy" size="small">
            <el-radio label="draft">仅生成草稿</el-radio>
            <el-radio label="immediate">生成后立即发布</el-radio>
            <el-radio label="scheduled">定时发布</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="generateForm.publishStrategy === 'scheduled'" label="发布时间">
          <el-date-picker
            v-model="generateForm.scheduledAt"
            type="datetime"
            placeholder="选择发布时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DDTHH:mm:ss"
            :disabled-date="disabledDate"
            :disabled-hours="disabledHours"
            :disabled-minutes="disabledMinutes"
            style="width: 220px"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="generating"
            :disabled="!generateForm.keywordId"
            @click="generateArticle"
          >
            <el-icon><MagicStick /></el-icon>
            生成文章
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 文章列表 -->
    <div class="section mt-20">
      <div class="section-header">
        <div class="header-left">
          <h2 class="section-title">文章列表</h2>
          <el-select
            v-model="filterProjectId"
            placeholder="全部项目"
            clearable
            style="width: 150px; margin-left: 16px;"
            size="small"
          >
            <el-option label="全部项目" :value="null" />
            <el-option
              v-for="p in validProjects"
              :key="p.id"
              :label="p.name"
              :value="p.id"
            />
          </el-select>

          <el-select
            v-model="filterPublishStatus"
            placeholder="全部状态"
            clearable
            style="width: 140px; margin-left: 12px;"
            size="small"
          >
            <el-option label="全部状态" :value="null" />
            <el-option label="已生成/待分发" value="completed" />
            <el-option label="已配置定时" value="scheduled" />
            <el-option label="生成中" value="generating" />
            <el-option label="生成失败" value="failed" />
            <el-option label="发布中" value="publishing" />
            <el-option label="已发布" value="published" />
          </el-select>
        </div>
        <el-button @click="loadArticles" size="small" type="primary" plain>
          <el-icon><Refresh /></el-icon>
          刷新列表
        </el-button>
      </div>

      <el-table
        v-loading="articlesLoading"
        :data="filteredArticles"
        stripe
        style="width: 100%"
        height="500"
      >
        <el-table-column prop="title" label="标题" min-width="180">
          <template #default="{ row }">
            <div class="title-cell">
              <span class="title-text">{{ row.title || '（内容生成中...）' }}</span>
              <el-tag v-if="isGenerating(row)" type="warning" size="small" style="margin-left: 8px;">
                生成中
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="生成状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getGenerateStatusType(row.publish_status)" size="small">
              {{ getGenerateStatusText(row.publish_status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="发布策略" width="120">
          <template #default="{ row }">
            <span class="text-muted" style="font-size: 12px;">
              {{ getStrategyDisplay(row) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="评分" width="70">
          <template #default="{ row }">
            <span v-if="row.quality_score" :class="getScoreClass(row.quality_score)">
              {{ row.quality_score }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            <span class="text-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="previewArticle(row)">预览</el-button>
            <el-button
              type="success"
              size="small"
              link
              :disabled="isGenerating(row)"
              @click="handleCheckQuality(row)"
            >质检</el-button>
            <el-button
              v-if="isGenerated(row)"
              type="info"
              size="small"
              link
              @click="goToBulkPublish"
            >去发布</el-button>
            <el-button type="danger" size="small" link @click="deleteArticle(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 文章预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="currentArticle?.title || '文章预览'"
      width="800px"
      destroy-on-close
    >
      <div v-if="currentArticle" class="article-preview-scroll">
        <div class="markdown-body" v-html="renderMarkdown(currentArticle.content)"></div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Refresh } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useWebSocket } from '@/composables/useWebSocket'
import { geoKeywordApi, geoArticleApi } from '@/services/api'
import MarkdownIt from 'markdown-it'

const router = useRouter()
const md = new MarkdownIt({ html: true, linkify: true })
const renderMarkdown = (content: string) => content ? md.render(content) : '暂无内容'

// 状态
const projects = ref<any[]>([])
const keywords = ref<any[]>([])
const articles = ref<any[]>([])
const articlesLoading = ref(false)
const generating = ref(false)
const showPreviewDialog = ref(false)
const currentArticle = ref<any>(null)
const filterProjectId = ref<number | null>(null)
const filterPublishStatus = ref<string | null>(null)

// 发布平台选项
const PLATFORM_OPTIONS = [
  { label: '知乎', value: 'zhihu' },
  { label: '搜狐', value: 'sohu' },
  { label: '百家号', value: 'baijiahao' },
  { label: '头条', value: 'toutiao' }
]

const generateForm = ref({
  projectId: null as number | null,
  keywordId: null as number | null,
  targetPlatforms: [] as string[],
  publishStrategy: 'draft' as 'draft' | 'immediate' | 'scheduled',
  scheduledAt: '' as string
})

// 🌟 有效项目列表（过滤掉没有 id 的项目，防止 el-option 报错）
const validProjects = computed(() => {
  return (projects.value || []).filter(p => p?.id !== undefined && p?.id !== null)
})

// 过滤后的文章
const filteredArticles = computed(() => {
  let result = articles.value

  // 按项目过滤
  if (filterProjectId.value !== null) {
    result = result.filter(a => {
      const keyword = keywords.value.find(k => k.id === a.keyword_id)
      return keyword && keyword.project_id === filterProjectId.value
    })
  }

  // 按发布状态过滤
  if (filterPublishStatus.value !== null) {
    result = result.filter(a => a.publish_status === filterPublishStatus.value)
  }

  return result
})

// 状态判断辅助函数
const isGenerating = (row: any) => row.publish_status === 'generating'
const isGenerated = (row: any) => ['completed', 'scheduled', 'published', 'publishing'].includes(row.publish_status)

// 数据加载
const loadProjects = async () => {
  try {
    const res: any = await geoKeywordApi.getProjects()
    projects.value = Array.isArray(res) ? res : (res?.data || [])
  } catch (error) { console.error(error) }
}

const onProjectChange = async () => {
  generateForm.value.keywordId = null
  keywords.value = []
  if (generateForm.value.projectId) {
    try {
      const res: any = await geoKeywordApi.getProjectKeywords(generateForm.value.projectId)
      keywords.value = Array.isArray(res) ? res : (res?.data || [])
    } catch (error) { console.error(error) }
  }
}

const loadArticles = async () => {
  articlesLoading.value = true
  try {
    const res: any = await geoArticleApi.getArticles()
    articles.value = Array.isArray(res) ? res : (res?.data || [])

    // 加载所有项目用于过滤
    if (projects.value.length === 0) {
      await loadProjects()
    }

    // 加载所有关键词用于过滤
    for (const article of articles.value) {
      const keyword = keywords.value.find(k => k.id === article.keyword_id)
      if (keyword && !keywords.value.find(k => k.id === keyword.id)) {
        keywords.value.push(keyword)
      }
    }
  } catch (error) {
    console.error('加载文章失败:', error)
  } finally {
    articlesLoading.value = false
  }
}

// 操作
const generateArticle = async () => {
  if (!generateForm.value.keywordId) return
  const project = projects.value.find(p => p.id === generateForm.value.projectId)

  generating.value = true
  try {
    const res = await geoArticleApi.generate({
      keyword_id: generateForm.value.keywordId as number,
      company_name: project?.company_name || '默认公司',
      // 新增：发布策略相关参数
      target_platforms: generateForm.value.targetPlatforms,
      publish_strategy: generateForm.value.publishStrategy,
      scheduled_at: generateForm.value.publishStrategy === 'scheduled' ? generateForm.value.scheduledAt : undefined
    })
    if (res.success) {
      const strategyText = {
        draft: '仅生成草稿',
        immediate: '立即发布',
        scheduled: '定时发布'
      }
      ElMessage.success(`任务提交成功，策略：${strategyText[generateForm.value.publishStrategy]}`)
      // 立即刷新列表以显示 generating 状态
      await loadArticles()

      // 启动轮询等待生成完成
      pollArticleGeneration()
    }
  } finally { generating.value = false }
}

// 轮询文章生成状态
const pollArticleGeneration = async () => {
  let pollCount = 0
  const maxPolls = 30 // 最多轮询 5 分钟

  const poll = async () => {
    if (pollCount >= maxPolls) {
      console.log('轮询超时，停止')
      return
    }

    pollCount++
    await loadArticles()

    // 检查是否有刚刚生成的文章变为 completed 状态
    const updatedArticle = articles.value.find(a => a.keyword_id === generateForm.value.keywordId)
    if (updatedArticle && updatedArticle.publish_status === 'completed') {
      console.log('文章生成完成')
      ElMessage.success('文章生成完成')
      return
    }

    // 如果文章状态为 failed，也停止
    if (updatedArticle && updatedArticle.publish_status === 'failed') {
      console.log('文章生成失败')
      ElMessage.error(updatedArticle.error_msg || '文章生成失败')
      return
    }

    // 1 秒后继续轮询
    setTimeout(poll, 2000)
  }

  await poll()
}

const handleCheckQuality = async (row: any) => {
  try {
    const res = await geoArticleApi.checkQuality(row.id)
    if (res.success) {
      ElMessage.success('质检评分已更新')
      await loadArticles()
    }
  } catch (e) { console.error(e) }
}

const deleteArticle = async (article: any) => {
  try {
    await ElMessageBox.confirm('确定要删除吗？', '警告', { type: 'warning' })
    await geoArticleApi.delete(article.id)
    ElMessage.success('已删除')
    await loadArticles()
  } catch (error) { }
}

const previewArticle = (article: any) => {
  currentArticle.value = article
  showPreviewDialog.value = true
}

// 前往批量发布页面
const goToBulkPublish = () => {
  // 将当前选择的关键词信息传递给发布页面
  router.push({
    path: '/publish/bulk',
    query: {
      projectId: filterProjectId.value,
      publishStatus: 'completed'
    }
  })
}

// 渲染工具
const getGenerateStatusType = (s: string) => {
  const statusMap: Record<string, string> = {
    generating: 'warning',     // 生成中
    completed: 'success',      // 已生成/待分发
    scheduled: 'primary',      // 已配置定时发布
    failed: 'danger',          // 生成失败
    publishing: 'primary',     // 发布中
    published: 'success',      // 已发布
    draft: 'info'             // 草稿
  }
  return statusMap[s] || 'info'
}

const getGenerateStatusText = (s: string) => {
  const textMap = {
    generating: '生成中',
    completed: '已生成/待分发',
    scheduled: '已配置定时发布',
    failed: '生成失败',
    publishing: '发布中',
    published: '已发布',
    draft: '草稿'
  }
  return textMap[s] || s
}

const getScoreClass = (s: number) => s >= 80 ? 'text-success' : (s >= 60 ? 'text-warning' : 'text-danger')
const formatDate = (d?: string) => d ? new Date(d).toLocaleString() : '-'

// 日期选择器辅助方法 - 禁用过去日期
const disabledDate = (time: Date) => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return time.getTime() < today.getTime()
}

// 日期选择器辅助方法 - 禁用过去的小时
const disabledHours = (hour: number) => {
  const now = new Date()
  const selectedDate = generateForm.value.scheduledAt ? new Date(generateForm.value.scheduledAt) : now
  if (selectedDate.toDateString() === now.toDateString()) {
    return hour < now.getHours()
  }
  return []
}

// 日期选择器辅助方法 - 禁用过去的分钟
const disabledMinutes = (hour: number, minute: number) => {
  const now = new Date()
  const selectedDate = generateForm.value.scheduledAt ? new Date(generateForm.value.scheduledAt) : now
  if (selectedDate.toDateString() === now.toDateString() && hour === now.getHours()) {
    return minute < now.getMinutes()
  }
  return []
}

// 获取发布策略显示文本
const getStrategyDisplay = (article: any) => {
  if (!article.publish_strategy || article.publish_strategy === 'draft') {
    return '仅草稿'
  }
  if (article.publish_strategy === 'immediate') {
    return '立即发布'
  }
  if (article.publish_strategy === 'scheduled' && article.scheduled_at) {
    const date = new Date(article.scheduled_at)
    return `定时: ${date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`
  }
  return article.publish_strategy || '未知'
}

onMounted(() => {
  loadProjects()
  loadArticles()

  // 🌟 连接 WebSocket 监听发布进度
  const { connect, disconnect, onPublishProgress } = useWebSocket()
  connect()

  // 监听发布进度事件，实时更新文章状态
  onPublishProgress((progressData: any) => {
    if (progressData.article_id && progressData.publish_status) {
      const articleIndex = articles.value.findIndex(a => a.id === progressData.article_id)
      if (articleIndex !== -1) {
        const oldStatus = articles.value[articleIndex].publish_status
        articles.value[articleIndex].publish_status = progressData.publish_status

        // 如果有 platform_url，也更新
        if (progressData.platform_url) {
          articles.value[articleIndex].platform_url = progressData.platform_url
        }

        // 如果有 error_msg，也更新
        if (progressData.error_msg) {
          articles.value[articleIndex].error_msg = progressData.error_msg
        }

        console.log(`[Articles] 文章状态已同步: article_id=${progressData.article_id}, ${oldStatus} -> ${progressData.publish_status}`)

        // 发布成功时显示提示
        if (progressData.status === 2 && oldStatus !== 'published') {
          const article = articles.value[articleIndex]
          ElMessage.success(`《${article.title?.substring(0, 20)}...》已成功发布`)
        }
      }
    }
  })

  // 保存 disconnect 函数用于清理
  ;(window as any).__wsDisconnect = disconnect
})

// 组件卸载时断开 WebSocket
onUnmounted(() => {
  if ((window as any).__wsDisconnect) {
    (window as any).__wsDisconnect()
    delete (window as any).__wsDisconnect
  }
})
</script>

<style scoped lang="scss">
.articles-page {
  padding: 20px;
}

.section {
  background: #1e1e1e;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.section-title {
  color: #fff;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: 600;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.text-muted {
  color: #888;
  font-size: 13px;
}

.text-success {
  color: #67c23a;
}

.text-warning {
  color: #e6a23c;
}

.text-danger {
  color: #f56c6c;
}

.article-preview-scroll {
  max-height: 70vh;
  overflow-y: auto;
  padding: 20px;
  background: #fff;
  color: #333;
  border-radius: 8px;
}

.markdown-body {
  line-height: 1.8;

  :deep(img) {
    max-width: 100%;
    border-radius: 8px;
    margin: 10px 0;
  }
}

.title-cell {
  display: flex;
  align-items: center;

  .title-text {
    flex: 1;
  }

  el-tag {
    flex-shrink: 0;
  }
}
</style>
