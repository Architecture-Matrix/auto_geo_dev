<template>
  <div class="publish-history-page">
    <h2>
      发布记录
      <el-button @click="loadRecords" size="small" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </h2>
    <el-table :data="records" stripe v-loading="loading">
      <el-table-column prop="article_title" label="文章标题" min-width="200" />
      <el-table-column prop="platform_name" label="平台" width="120">
        <template #default="{ row }">
          <el-tag :color="getPlatformColor(row.platform)">
            {{ row.platform_name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="account_name" label="账号" width="120" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="published_at" label="发布时间" width="180" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button v-if="row.platform_url" text type="primary" @click="openUrl(row.platform_url)">
            查看文章
          </el-button>
          <el-button
            v-else-if="row.status === 0"
            text
            type="primary"
            @click="triggerPublish(row)"
          >
            立即触发
          </el-button>
          <el-button v-else-if="row.status === 3" text type="warning" @click="retry(row)">
            重试
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { PLATFORMS } from '@/core/config/platform'
import { publishApi } from '@/services/api'

interface PublishRecord {
  id: number
  article_id: number
  article_title: string
  account_id: number
  account_name: string
  platform: string
  platform_name: string
  status: number
  platform_url?: string
  error_msg?: string
  retry_count?: number
  created_at?: string
  published_at?: string
}

const records = ref<PublishRecord[]>([])
const loading = ref(false)

const loadRecords = async () => {
  loading.value = true
  try {
    const data = await publishApi.getRecords({ limit: 50 })
    if (Array.isArray(data)) {
      records.value = data
    }
  } catch (error) {
    console.error('获取发布记录失败:', error)
    ElMessage.error('获取发布记录失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadRecords)

const openUrl = (url: string) => {
  window.open(url, '_blank')
}

const retry = async (record: PublishRecord) => {
  try {
    const result = await publishApi.retry(record.id)
    if (result.success) {
      ElMessage.success('重试任务已创建')
      await loadRecords()
    } else {
      ElMessage.error(result.message || '重试失败')
    }
  } catch (error) {
    console.error('重试失败:', error)
    ElMessage.error('重试失败')
  }
}

const triggerPublish = async (record: PublishRecord) => {
  try {
    const response = await publishApi.trigger(record.article_id)
    const result = response.data || response
    if (result.success !== false) {
      ElMessage.success('立即触发已执行，文章正在发布中')
      // 刷新记录列表
      await loadRecords()
    } else {
      ElMessage.error(result.message || '触发发布失败')
    }
  } catch (error) {
    console.error('触发发布失败:', error)
    ElMessage.error('触发发布失败')
  }
}

const getPlatformColor = (platform: string) => {
  return PLATFORMS[platform]?.color || '#666'
}

const getStatusType = (status: number) => {
  const types: Record<number, string> = { 0: 'info', 1: 'warning', 2: 'success', 3: 'danger' }
  return types[status] || 'info'
}

const getStatusText = (status: number) => {
  const texts: Record<number, string> = { 0: '待发布', 1: '发布中', 2: '成功', 3: '失败' }
  return texts[status] || '未知'
}
</script>

<style scoped lang="scss">
.publish-history-page {
  display: flex;
  flex-direction: column;
  gap: 20px;

  h2 {
    margin: 0;
  }
}
</style>
