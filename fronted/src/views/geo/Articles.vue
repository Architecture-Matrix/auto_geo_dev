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
            v-model="generateForm.keywordId"
            placeholder="请选择关键词"
            style="width: 200px"
            :disabled="!generateForm.projectId"
          >
            <el-option
              v-for="keyword in currentKeywords"
              :key="keyword.id"
              :label="keyword.keyword"
              :value="keyword.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="发布平台">
          <el-select v-model="generateForm.platform" style="width: 150px">
            <el-option label="知乎" value="zhihu" />
            <el-option label="百家号" value="baijiahao" />
            <el-option label="搜狐号" value="sohu" />
            <el-option label="头条号" value="toutiao" />
          </el-select>
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
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">文章列表</h2>
        <el-button @click="loadArticles">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <el-table
        v-loading="articlesLoading"
        :data="articles"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            {{ row.title || '（无标题）' }}
          </template>
        </el-table-column>
        <el-table-column prop="platform" label="平台" width="120">
          <template #default="{ row }">
            <el-tag>{{ getPlatformName(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="质检状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getQualityStatusType(row.quality_status)">
              {{ getQualityStatusText(row.quality_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="质量评分" width="100">
          <template #default="{ row }">
            <span v-if="row.quality_score" :class="getScoreClass(row.quality_score)">
              {{ row.quality_score }}分
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="AI味" width="100">
          <template #default="{ row }">
            <span v-if="row.ai_score" :class="getAiScoreClass(row.ai_score)">
              {{ row.ai_score }}%
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="可读性" width="100">
          <template #default="{ row }">
            <span v-if="row.readability_score" :class="getReadabilityClass(row.readability_score)">
              {{ row.readability_score }}分
            </span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="previewArticle(row)">
              预览
            </el-button>
            <el-button
              type="success"
              size="small"
              link
              :loading="checkingQuality === row.id"
              :disabled="row.quality_status === 'passed'"
              @click="checkQuality(row)"
            >
              质检
            </el-button>
            <el-button type="info" size="small" link @click="editArticle(row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" link @click="deleteArticle(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 文章预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="currentArticle?.title || '文章预览'"
      width="800px"
    >
      <div v-if="currentArticle" class="article-preview">
        <div class="article-meta">
          <el-tag>{{ getPlatformName(currentArticle.platform) }}</el-tag>
          <span class="article-date">{{ formatDate(currentArticle.created_at) }}</span>
        </div>
        <div class="article-content">{{ currentArticle.content }}</div>
      </div>
      <template #footer>
        <el-button @click="showPreviewDialog = false">关闭</el-button>
        <el-button
          type="success"
          :loading="checkingQuality === currentArticle?.id"
          @click="checkQuality(currentArticle!)"
        >
          质检
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑文章对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑文章"
      width="800px"
    >
      <el-form v-if="editForm" :model="editForm" label-width="80px">
        <el-form-item label="标题">
          <el-input
            v-model="editForm.title"
            placeholder="请输入文章标题"
          />
        </el-form-item>
        <el-form-item label="正文">
          <el-input
            v-model="editForm.content"
            type="textarea"
            :rows="15"
            placeholder="请输入文章正文"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveArticle">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 质检结果对话框 -->
    <el-dialog
      v-model="showQualityDialog"
      title="质检结果"
      width="500px"
    >
      <div v-if="qualityResult" class="quality-result">
        <div class="quality-item">
          <div class="quality-label">质量评分</div>
          <div class="quality-value" :class="getScoreClass(qualityResult.quality_score || 0)">
            {{ qualityResult.quality_score || '-' }}分
          </div>
        </div>
        <div class="quality-item">
          <div class="quality-label">AI味检测</div>
          <div class="quality-value" :class="getAiScoreClass(qualityResult.ai_score || 0)">
            {{ qualityResult.ai_score || '-' }}%
          </div>
          <div class="quality-tip">AI味越高表示越像AI生成</div>
        </div>
        <div class="quality-item">
          <div class="quality-label">可读性评分</div>
          <div class="quality-value" :class="getReadabilityClass(qualityResult.readability_score || 0)">
            {{ qualityResult.readability_score || '-' }}分
          </div>
        </div>
        <div class="quality-status">
          <el-tag :type="getQualityStatusType(qualityResult.quality_status)" size="large">
            {{ getQualityStatusText(qualityResult.quality_status) }}
          </el-tag>
        </div>
      </div>
      <template #footer>
        <el-button @click="showQualityDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  MagicStick,
  Refresh,
} from '@element-plus/icons-vue'
import { geoKeywordApi, geoArticleApi } from '@/services/api'

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

interface Article {
  id: number
  keyword_id: number
  title?: string
  content: string
  platform?: string
  quality_score?: number
  ai_score?: number
  readability_score?: number
  quality_status: string
  created_at: string
}

interface QualityResult {
  article_id: number
  quality_score?: number
  ai_score?: number
  readability_score?: number
  quality_status: string
}

// ==================== 状态 ====================
const projects = ref<Project[]>([])
const keywords = ref<Keyword[]>([])
const articles = ref<Article[]>([])

const projectsLoading = ref(false)
const articlesLoading = ref(false)
const generating = ref(false)
const checkingQuality = ref<number | null>(null)
const saving = ref(false)

const currentArticle = ref<Article | null>(null)
const qualityResult = ref<QualityResult | null>(null)
const editForm = ref<{ title?: string; content?: string } | null>(null)

// 对话框状态
const showPreviewDialog = ref(false)
const showEditDialog = ref(false)
const showQualityDialog = ref(false)

// 生成表单
const generateForm = ref({
  projectId: null as number | null,
  keywordId: null as number | null,
  platform: 'zhihu',
})

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
  generateForm.value.keywordId = null
  if (generateForm.value.projectId) {
    try {
      const result = await geoKeywordApi.getProjectKeywords(generateForm.value.projectId)
      keywords.value = result || []
    } catch (error) {
      console.error('加载关键词失败:', error)
    }
  }
}

// 加载文章列表
const loadArticles = async () => {
  articlesLoading.value = true
  try {
    const result = await geoArticleApi.getList({ limit: 100 })
    articles.value = result || []
  } catch (error) {
    console.error('加载文章失败:', error)
  } finally {
    articlesLoading.value = false
  }
}

// 生成文章
const generateArticle = async () => {
  if (!generateForm.value.keywordId) {
    ElMessage.warning('请选择关键词')
    return
  }

  const project = projects.value.find(p => p.id === generateForm.value.projectId)
  if (!project) {
    ElMessage.warning('请选择项目')
    return
  }

  generating.value = true
  try {
    const result = await geoArticleApi.generate({
      keyword_id: generateForm.value.keywordId,
      company_name: project.company_name,
      platform: generateForm.value.platform,
    })

    if (result.success) {
      await loadArticles()
      ElMessage.success(result.message || '文章生成成功')
    } else {
      ElMessage.error(result.message || '文章生成失败')
    }
  } catch (error) {
    console.error('文章生成失败:', error)
    ElMessage.error('文章生成失败')
  } finally {
    generating.value = false
  }
}

// 预览文章
const previewArticle = (article: Article) => {
  currentArticle.value = article
  showPreviewDialog.value = true
}

// 质检文章
const checkQuality = async (article: Article) => {
  checkingQuality.value = article.id
  try {
    const result = await geoArticleApi.checkQuality(article.id)

    if (result.success) {
      qualityResult.value = result.data
      showQualityDialog.value = true
      showPreviewDialog.value = false
      await loadArticles()
      ElMessage.success('质检完成')
    } else {
      ElMessage.error(result.message || '质检失败')
    }
  } catch (error) {
    console.error('质检失败:', error)
    ElMessage.error('质检失败')
  } finally {
    checkingQuality.value = null
  }
}

// 编辑文章
const editArticle = (article: Article) => {
  editForm.value = {
    title: article.title,
    content: article.content,
  }
  currentArticle.value = article
  showEditDialog.value = true
}

// 保存文章
const saveArticle = async () => {
  if (!currentArticle.value || !editForm.value) return

  saving.value = true
  try {
    await geoArticleApi.update(currentArticle.value.id, {
      title: editForm.value.title,
      content: editForm.value.content,
    })
    showEditDialog.value = false
    await loadArticles()
    ElMessage.success('保存成功')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 删除文章
const deleteArticle = async (article: Article) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这篇文章吗？',
      '确认删除',
      { type: 'warning' }
    )

    await geoArticleApi.delete(article.id)
    articles.value = articles.value.filter(a => a.id !== article.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除文章失败:', error)
    }
  }
}

// 获取平台名称
const getPlatformName = (platform?: string) => {
  const names: Record<string, string> = {
    zhihu: '知乎',
    baijiahao: '百家号',
    sohu: '搜狐号',
    toutiao: '头条号',
  }
  return names[platform || ''] || platform || '-'
}

// 获取质检状态类型
const getQualityStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'warning',
    passed: 'success',
    failed: 'danger',
  }
  return types[status] || 'info'
}

// 获取质检状态文本
const getQualityStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待质检',
    passed: '已通过',
    failed: '未通过',
  }
  return texts[status] || status
}

// 获取分数样式类
const getScoreClass = (score: number) => {
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  return 'score-poor'
}

const getAiScoreClass = (score: number) => {
  if (score >= 70) return 'score-high-ai'
  if (score >= 40) return 'score-medium-ai'
  return 'score-low-ai'
}

const getReadabilityClass = (score: number) => {
  if (score >= 80) return 'score-excellent'
  if (score >= 60) return 'score-good'
  return 'score-poor'
}

// 格式化日期
const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadProjects()
  loadArticles()
})
</script>

<style scoped lang="scss">
.articles-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
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

.generate-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.article-preview {
  .article-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);

    .article-date {
      color: var(--text-secondary);
      font-size: 14px;
    }
  }

  .article-content {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.8;
    color: var(--text-primary);
    max-height: 500px;
    overflow-y: auto;
  }
}

.quality-result {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px 0;

  .quality-item {
    display: flex;
    align-items: center;
    gap: 16px;

    .quality-label {
      width: 100px;
      font-size: 14px;
      color: var(--text-secondary);
    }

    .quality-value {
      font-size: 24px;
      font-weight: 600;

      &.score-excellent {
        color: #67c23a;
      }

      &.score-good {
        color: #e6a23c;
      }

      &.score-poor {
        color: #f56c6c;
      }

      &.score-high-ai {
        color: #f56c6c;
      }

      &.score-medium-ai {
        color: #e6a23c;
      }

      &.score-low-ai {
        color: #67c23a;
      }
    }

    .quality-tip {
      font-size: 12px;
      color: var(--text-muted);
    }
  }

  .quality-status {
    display: flex;
    justify-content: center;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }
}

.text-muted {
  color: var(--text-muted);
}

.score-excellent { color: #67c23a; }
.score-good { color: #e6a23c; }
.score-poor { color: #f56c6c; }
.score-high-ai { color: #f56c6c; }
.score-medium-ai { color: #e6a23c; }
.score-low-ai { color: #67c23a; }

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
