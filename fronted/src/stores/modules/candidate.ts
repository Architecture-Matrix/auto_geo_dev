/**
 * 候选人状态管理
 * 用这个来管理候选人数据！
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Candidate {
  id: number
  uid: string
  detail: any
  attached: any
  is_send: boolean
  article_id: number | null
  status: number
  remark: string
  created_at: string
  sent_at: string | null
}

export const useCandidateStore = defineStore('candidate', () => {
  // ==================== 状态 ====================

  /** 候选人列表 */
  const candidates = ref<Candidate[]>([])

  /** 加载状态 */
  const loading = ref(false)

  /** 错误信息 */
  const error = ref<string | null>(null)

  /** 分页信息 */
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0,
  })

  // ==================== 计算属性 ====================

  /** 待发送候选人 */
  const pendingCandidates = computed(() => {
    return candidates.value.filter(c => !c.is_send && c.status === 1)
  })

  /** 已发送候选人 */
  const sentCandidates = computed(() => {
    return candidates.value.filter(c => c.is_send)
  })

  /** 总数 */
  const totalCount = computed(() => pagination.value.total)

  // ==================== 操作 ====================

  /**
   * 加载候选人列表
   */
  async function loadCandidates(params: {
    page?: number
    pageSize?: number
    status?: number
    is_send?: boolean
    keyword?: string
  } = {}) {
    loading.value = true
    error.value = null

    try {
      const queryParams = new URLSearchParams()
      if (params.page) queryParams.append('page', String(params.page))
      if (params.pageSize) queryParams.append('limit', String(params.pageSize))
      if (params.status !== undefined) queryParams.append('status', String(params.status))
      if (params.is_send !== undefined) queryParams.append('is_send', String(params.is_send))
      if (params.keyword) queryParams.append('keyword', params.keyword)

      const url = `/api/candidates?${queryParams.toString()}`
      const response = await fetch(url)
      const data = await response.json()

      if (data.success !== false) {
        candidates.value = data.items || []
        pagination.value.total = data.total || 0
        pagination.value.page = params.page || 1
      } else {
        error.value = data.message || '加载失败'
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
    } finally {
      loading.value = false
    }
  }

  /**
   * 同步候选人（n8n webhook调用）
   */
  async function syncCandidate(data: any) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch('/api/candidates/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      const result = await response.json()

      if (result.success !== false) {
        await loadCandidates()
        return { success: true, data: result.data }
      } else {
        error.value = result.message || '同步失败'
        return { success: false, message: error.value }
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  /**
   * 发送文章给候选人
   */
  async function sendToCandidate(candidateId: number, articleId: number) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`/api/candidates/${candidateId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ article_id: articleId }),
      })
      const result = await response.json()

      if (result.success !== false) {
        const candidate = candidates.value.find(c => c.id === candidateId)
        if (candidate) {
          candidate.is_send = true
          candidate.article_id = articleId
          candidate.sent_at = new Date().toISOString()
        }
        return { success: true, data: result.data }
      } else {
        error.value = result.message || '发送失败'
        return { success: false, message: error.value }
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除候选人
   */
  async function deleteCandidate(id: number) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`/api/candidates/${id}`, {
        method: 'DELETE',
      })
      const result = await response.json()

      if (result.success !== false) {
        candidates.value = candidates.value.filter(c => c.id !== id)
        return { success: true }
      } else {
        error.value = result.message || '删除失败'
        return { success: false, message: error.value }
      }
    } catch (e: any) {
      error.value = e.message || '网络错误'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  return {
    candidates,
    loading,
    error,
    pagination,
    pendingCandidates,
    sentCandidates,
    totalCount,
    loadCandidates,
    syncCandidate,
    sendToCandidate,
    deleteCandidate,
  }
})
