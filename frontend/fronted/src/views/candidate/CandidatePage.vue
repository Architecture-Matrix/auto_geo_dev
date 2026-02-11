<template>
  <div class="candidate-page">
    <!-- 顶部统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon" style="background: #6366f1">
          <el-icon><User /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">总候选人</div>
          <div class="stat-value">{{ stats.total }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #22c55e">
          <el-icon><CircleCheck /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">已发送</div>
          <div class="stat-value">{{ stats.sent }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f59e0b">
          <el-icon><Clock /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">待发送</div>
          <div class="stat-value">{{ stats.pending }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #8b5cf6">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">发送率</div>
          <div class="stat-value">{{ stats.send_rate }}%</div>
        </div>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索候选人 UID"
          clearable
          style="width: 200px"
          @change="loadCandidates"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="loadCandidates">
          <el-option label="全部" :value="null" />
          <el-option label="有效" :value="1" />
          <el-option label="无效" :value="0" />
        </el-select>

        <el-select v-model="filterSend" placeholder="发送状态" clearable style="width: 120px" @change="loadCandidates">
          <el-option label="全部" :value="null" />
          <el-option label="已发送" :value="true" />
          <el-option label="待发送" :value="false" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <el-button type="primary" @click="showSyncDialog">
          <el-icon><Plus /></el-icon>
          同步候选人
        </el-button>
      </div>
    </div>

    <!-- 候选人表格 -->
    <div class="table-container">
      <el-table
        :data="candidates"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="uid" label="UID" width="150" />
        <el-table-column label="详细信息" min-width="200">
          <template #default="{ row }">
            <div class="detail-cell">
              {{ formatDetail(row.detail) }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="发送状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_send ? 'success' : 'warning'" size="small">
              {{ row.is_send ? '已发送' : '待发送' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_send"
              type="primary"
              size="small"
              @click="showSendDialog(row)"
            >
              发送文章
            </el-button>
            <el-button
              v-else
              size="small"
              @click="viewArticle(row)"
            >
              查看文章
            </el-button>
            <el-button
              size="small"
              @click="editCandidate(row)"
            >
              编辑
            </el-button>
            <el-popconfirm
              title="确定删除吗？"
              @confirm="deleteCandidate(row.id)"
            >
              <template #reference>
                <el-button type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadCandidates"
          @current-change="loadCandidates"
        />
      </div>
    </div>

    <!-- 同步对话框 -->
    <el-dialog v-model="syncDialogVisible" title="同步候选人" width="600px">
      <el-form :model="syncForm" label-width="80px">
        <el-form-item label="UID">
          <el-input v-model="syncForm.uid" placeholder="请输入候选人唯一标识" />
        </el-form-item>
        <el-form-item label="详细信息">
          <el-input
            v-model="syncForm.detail"
            type="textarea"
            :rows="3"
            placeholder='JSON格式，例如：{"name": "张三", "position": "工程师"}'
          />
        </el-form-item>
        <el-form-item label="附件">
          <el-input
            v-model="syncForm.attached"
            type="textarea"
            :rows="2"
            placeholder='JSON格式，例如：{"resume_url": "https://..."}'
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="syncDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="syncCandidate">确定</el-button>
      </template>
    </el-dialog>

    <!-- 发送文章对话框 -->
    <el-dialog v-model="sendDialogVisible" title="发送文章" width="500px">
      <el-form :model="sendForm" label-width="80px">
        <el-form-item label="候选人">
          <el-input :value="currentCandidate?.uid" disabled />
        </el-form-item>
        <el-form-item label="选择文章">
          <el-select v-model="sendForm.article_id" placeholder="请选择文章" style="width: 100%">
            <el-option
              v-for="article in articles"
              :key="article.id"
              :label="article.title"
              :value="article.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sendDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="sendToCandidate">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  User, CircleCheck, Clock, TrendCharts, Search, Plus
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// 状态
const loading = ref(false)
const candidates = ref<any[]>([])
const articles = ref<any[]>([])

// 筛选
const searchKeyword = ref('')
const filterStatus = ref<number | null>(null)
const filterSend = ref<boolean | null>(null)

// 分页
const pagination = ref({
  page: 1,
  limit: 20,
  total: 0
})

// 统计
const stats = ref({
  total: 0,
  sent: 0,
  pending: 0,
  send_rate: 0
})

// 对话框
const syncDialogVisible = ref(false)
const sendDialogVisible = ref(false)
const syncForm = ref({
  uid: '',
  detail: '',
  attached: ''
})
const sendForm = ref({
  article_id: null as number | null
})
const currentCandidate = ref<any>(null)

// 加载候选人列表
const loadCandidates = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.append('page', String(pagination.value.page))
    params.append('limit', String(pagination.value.limit))
    if (filterStatus.value !== null) params.append('status', String(filterStatus.value))
    if (filterSend.value !== null) params.append('is_send', String(filterSend.value))
    if (searchKeyword.value) params.append('keyword', searchKeyword.value)

    const response = await fetch(`/api/candidates?${params}`)
    const data = await response.json()

    if (data.success !== false) {
      candidates.value = data.items || []
      pagination.value.total = data.total || 0
    }
  } catch (e: any) {
    ElMessage.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

// 加载统计数据
const loadStats = async () => {
  try {
    const response = await fetch('/api/candidates/stats/overview')
    const data = await response.json()
    if (data.success) {
      stats.value = data.data
    }
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

// 加载文章列表
const loadArticles = async () => {
  try {
    const response = await fetch('/api/articles?limit=100')
    const data = await response.json()
    if (data.success !== false) {
      articles.value = data.items || []
    }
  } catch (e) {
    console.error('加载文章失败', e)
  }
}

// 显示同步对话框
const showSyncDialog = () => {
  syncForm.value = { uid: '', detail: '', attached: '' }
  syncDialogVisible.value = true
}

// 同步候选人
const syncCandidate = async () => {
  if (!syncForm.value.uid) {
    ElMessage.warning('请输入 UID')
    return
  }

  try {
    const payload = {
      uid: syncForm.value.uid,
      detail: syncForm.value.detail ? JSON.parse(syncForm.value.detail) : null,
      attached: syncForm.value.attached ? JSON.parse(syncForm.value.attached) : null,
      is_send: false
    }

    const response = await fetch('/api/candidates/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const data = await response.json()
    if (data.success) {
      ElMessage.success('同步成功')
      syncDialogVisible.value = false
      loadCandidates()
      loadStats()
    } else {
      ElMessage.error(data.message || '同步失败')
    }
  } catch (e: any) {
    ElMessage.error('同步失败: ' + e.message)
  }
}

// 显示发送对话框
const showSendDialog = (candidate: any) => {
  currentCandidate.value = candidate
  sendForm.value.article_id = null
  sendDialogVisible.value = true
}

// 发送文章
const sendToCandidate = async () => {
  if (!sendForm.value.article_id) {
    ElMessage.warning('请选择文章')
    return
  }

  try {
    const response = await fetch(`/api/candidates/${currentCandidate.value.id}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_id: sendForm.value.article_id })
    })

    const data = await response.json()
    if (data.success) {
      ElMessage.success('发送成功')
      sendDialogVisible.value = false
      loadCandidates()
      loadStats()
    } else {
      ElMessage.error(data.message || '发送失败')
    }
  } catch (e: any) {
    ElMessage.error('发送失败: ' + e.message)
  }
}

// 查看文章
const viewArticle = (candidate: any) => {
  if (candidate.article_id) {
    window.open(`/articles/${candidate.article_id}`, '_blank')
  }
}

// 编辑候选人
const editCandidate = (candidate: any) => {
  // TODO: 实现编辑功能
  ElMessage.info('编辑功能待实现')
}

// 删除候选人
const deleteCandidate = async (id: number) => {
  try {
    const response = await fetch(`/api/candidates/${id}`, { method: 'DELETE' })
    const data = await response.json()
    if (data.success) {
      ElMessage.success('删除成功')
      loadCandidates()
      loadStats()
    } else {
      ElMessage.error(data.message || '删除失败')
    }
  } catch (e: any) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

// 格式化详情
const formatDetail = (detail: any) => {
  if (!detail) return '-'
  if (typeof detail === 'string') return detail
  return JSON.stringify(detail, null, 2)
}

// 格式化日期
const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadCandidates()
  loadStats()
  loadArticles()
})
</script>

<style scoped lang="scss">
.candidate-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;

  .stat-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
    background: var(--bg-secondary);
    border-radius: 12px;

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 24px;
    }

    .stat-content {
      .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }
  }
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .toolbar-left {
    display: flex;
    gap: 12px;
  }
}

.table-container {
  background: var(--bg-secondary);
  border-radius: 12px;
  padding: 16px;

  .detail-cell {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-secondary);
    font-size: 12px;
  }

  .pagination {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
