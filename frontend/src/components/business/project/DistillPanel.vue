<template>
  <div class="distill-panel">
    <!-- 头部 -->
    <div class="panel-header">
      <div class="header-left">
        <div class="header-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <h3 class="header-title">关键词蒸馏</h3>
          <span v-if="currentProject" class="header-project">{{ currentProject.name }}</span>
          <span v-else class="header-hint">请先选择项目</span>
        </div>
      </div>
      <button
        v-if="results.length > 0"
        class="clear-btn"
        @click="clearResults"
      >
        <svg viewBox="0 0 16 16" fill="currentColor" width="14">
          <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z"/>
          <path fill-rule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
        </svg>
        清空
      </button>
    </div>

    <!-- 蒸馏输入区 -->
    <div class="distill-form" :class="{ disabled: !currentProject }">
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">
            <svg viewBox="0 0 16 16" fill="currentColor" width="14">
              <path d="M6.5 2a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1zm3 0a.5.5 0 01.5.5v1a.5.5 0 01-.5.5h-1a.5.5 0 01-.5-.5v-1a.5.5 0 01.5-.5h1z"/>
            </svg>
            领域关键词
          </label>
          <div class="input-wrapper">
            <input
              v-model="distillForm.keyword"
              type="text"
              class="form-input"
              placeholder="如：无人机清洗"
              :disabled="!currentProject"
              @keyup.enter="startDistill"
            >
            <div v-if="isSynced" class="sync-badge" title="已同步项目信息">
              <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
              </svg>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">
            <svg viewBox="0 0 16 16" fill="currentColor" width="14">
              <path d="M8 1a4 4 0 00-4 4v2H2v2h2v6a2 2 0 002 2h4a2 2 0 002-2V9h2V7h-2V5a4 4 0 00-4-4zm0 2a2 2 0 012 2v2H6V5a2 2 0 012-2z"/>
            </svg>
            公司名称
          </label>
          <div class="input-wrapper">
            <input
              v-model="distillForm.company"
              type="text"
              class="form-input"
              placeholder="自动填充"
              :disabled="!currentProject"
              @keyup.enter="startDistill"
            >
            <div v-if="isSynced" class="sync-badge" title="已同步项目信息">
              <svg viewBox="0 0 16 16" fill="currentColor" width="12">
                <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- 示例提示 -->
      <div v-if="!distilling && results.length === 0" class="example-tip">
        <svg viewBox="0 0 16 16" fill="currentColor" width="16">
          <path d="M8 16A8 8 0 108 0a8 8 0 000 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 110-2 1 1 0 010 2z"/>
        </svg>
        <span>示例：「无人机清洗」+「绿阳环保」→ 无人机清洗哪家强？无人机清洗推荐？</span>
      </div>

      <!-- 蒸馏按钮 -->
      <button
        class="distill-btn"
        :class="{ loading: distilling, disabled: !canDistill }"
        :disabled="!canDistill"
        @click="startDistill"
      >
        <span v-if="!distilling" class="btn-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
        </span>
        <span v-else class="btn-spinner"></span>
        <span class="btn-text">{{ distilling ? '蒸馏中...' : '开始蒸馏' }}</span>
      </button>
    </div>

    <!-- 蒸馏结果区 -->
    <div v-if="results.length > 0 || distilling" class="distill-results">
      <div class="results-header">
        <h4 class="results-title">
          <svg viewBox="0 0 16 16" fill="currentColor" width="16">
            <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
          </svg>
          蒸馏结果
          <span class="results-count">({{ results.length }})</span>
        </h4>
        <button
          v-if="hasUnsaved"
          class="save-all-btn"
          @click="saveAll"
        >
          <svg viewBox="0 0 16 16" fill="currentColor" width="14">
            <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
          </svg>
          全部保存
        </button>
      </div>

      <div class="results-list">
        <!-- 加载骨架屏 -->
        <template v-if="distilling && results.length === 0">
          <div v-for="i in 3" :key="'skeleton-' + i" class="result-skeleton">
            <div class="skeleton-number"></div>
            <div class="skeleton-content">
              <div class="skeleton-keyword"></div>
              <div class="skeleton-questions">
                <div class="skeleton-question"></div>
                <div class="skeleton-question"></div>
              </div>
            </div>
          </div>
        </template>

        <!-- 结果列表 -->
        <TransitionGroup name="result">
          <div
            v-for="(result, index) in results"
            :key="result.id"
            class="result-item"
            :class="{ saved: result.saved }"
          >
            <div class="result-number">{{ index + 1 }}</div>
            <div class="result-content">
              <div class="result-keyword">
                <span class="keyword-tag">{{ result.keyword }}</span>
              </div>
              <div class="result-questions">
                <div
                  v-for="(q, qIndex) in result.questions"
                  :key="qIndex"
                  class="question-chip"
                >
                  {{ q }}
                </div>
              </div>
            </div>
            <div class="result-action">
              <button
                v-if="!result.saved"
                class="action-btn save"
                @click="saveResult(result)"
              >
                保存
              </button>
              <span v-else class="saved-badge">
                <svg viewBox="0 0 16 16" fill="currentColor" width="14">
                  <path d="M10.97 4.97a.75.75 0 011.07 1.05l-3.99 4.99a.75.75 0 01-1.08.02L4.324 8.384a.75.75 0 111.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 01.02-.022z"/>
                </svg>
                已保存
              </span>
            </div>
          </div>
        </TransitionGroup>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { geoKeywordApi } from '@/services/api'

// ==================== 类型定义 ====================
interface Project {
  id: number
  name: string
  company_name: string
  domain_keyword?: string
  industry?: string
  description?: string
}

interface DistillResult {
  id: string
  keyword: string
  questions: string[]
  saved: boolean
}

// ==================== Props ====================
interface Props {
  currentProject: Project | null
}

const props = defineProps<Props>()

// ==================== 状态 ====================
const distilling = ref(false)
const results = ref<DistillResult[]>([])

const distillForm = ref({
  keyword: '',
  company: '',
})

// ==================== 计算属性 ====================
const canDistill = computed(() => {
  return props.currentProject &&
    distillForm.value.keyword.trim() &&
    distillForm.value.company.trim()
})

const isSynced = computed(() => {
  if (!props.currentProject) return false
  return distillForm.value.keyword === props.currentProject.domain_keyword &&
    distillForm.value.company === props.currentProject.company_name
})

const hasUnsaved = computed(() => {
  return results.value.some(r => !r.saved)
})

// ==================== 方法 ====================

// 监听项目变化，同步表单
watch(() => props.currentProject, (project) => {
  if (project) {
    distillForm.value.keyword = project.domain_keyword || ''
    distillForm.value.company = project.company_name || ''
    results.value = []
  } else {
    distillForm.value.keyword = ''
    distillForm.value.company = ''
    results.value = []
  }
}, { immediate: true })

// 开始蒸馏
const startDistill = async () => {
  if (!canDistill.value) {
    ElMessage.warning('请输入关键词和公司名称')
    return
  }

  distilling.value = true
  try {
    const result = await geoKeywordApi.distill({
      project_id: props.currentProject!.id,
      company_name: distillForm.value.company,
      industry: props.currentProject?.industry || '',
      description: props.currentProject?.description || '',
      count: 5,
    })

    if (result.success && result.data?.keywords) {
      const keywords = result.data.keywords
      for (const kw of keywords) {
        const questionsResult = await geoKeywordApi.generateQuestions({
          keyword_id: kw.id,
          count: 3,
        })

        results.value.push({
          id: kw.id.toString(),
          keyword: kw.keyword,
          questions: questionsResult.data?.questions?.map((q: any) => q.question) || [],
          saved: true,
        })
      }

      // 触发刷新事件
      emit('refresh')
      ElMessage.success(`蒸馏完成，生成 ${keywords.length} 个关键词`)
    } else {
      ElMessage.error(result.message || '蒸馏失败')
    }
  } catch (error) {
    console.error('蒸馏失败:', error)
    ElMessage.error('蒸馏失败，请稍后重试')
  } finally {
    distilling.value = false
  }
}

// 保存单个结果
const saveResult = async (result: DistillResult) => {
  try {
    result.saved = true
    ElMessage.success('保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

// 全部保存
const saveAll = async () => {
  for (const result of results.value) {
    if (!result.saved) {
      await saveResult(result)
    }
  }
}

// 清空结果
const clearResults = () => {
  results.value = []
}

// ==================== Emits ====================
const emit = defineEmits<{
  refresh: []
}>()
</script>

<style scoped lang="scss">
.distill-panel {
  display: flex;
  flex-direction: column;
  background: #f8f9fc;
  border-radius: 12px;
  overflow: hidden;
}

// 头部
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: white;
  border-bottom: 1px solid #e8ecf1;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .header-icon {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: linear-gradient(135deg, #10b981 0%, #059669 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;

      svg {
        width: 18px;
        height: 18px;
      }
    }

    .header-title {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: #1a1f36;
    }

    .header-project {
      font-size: 12px;
      color: #4a90e2;
    }

    .header-hint {
      font-size: 12px;
      color: #9ca3af;
    }
  }

  .clear-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    background: #fef2f2;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    color: #ef4444;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: #fee2e2;
    }
  }
}

// 蒸馏表单
.distill-form {
  padding: 16px;
  background: white;
  margin: 12px;
  border-radius: 12px;

  &.disabled {
    opacity: 0.6;
    pointer-events: none;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }

  .form-group {
    .form-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 500;
      color: #374151;
      margin-bottom: 6px;
    }

    .input-wrapper {
      position: relative;

      .form-input {
        width: 100%;
        padding: 10px 40px 10px 12px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        font-size: 13px;
        color: #1a1f36;
      }

      .sync-badge {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        width: 18px;
        height: 18px;
        background: #d1fae5;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #059669;
      }
    }
  }

  .example-tip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    background: linear-gradient(135deg, rgba(74, 144, 226, 0.08) 0%, rgba(74, 144, 226, 0.04) 100%);
    border-radius: 8px;
    margin-bottom: 12px;
    font-size: 12px;
    color: #6b7280;

    svg {
      color: #4a90e2;
      flex-shrink: 0;
    }
  }

  .distill-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 24px;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    color: white;
    cursor: pointer;
    transition: all 0.3s ease;

    &:hover:not(.disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }

    &.disabled {
      background: #e5e7eb;
      cursor: not-allowed;
    }

    &.loading {
      background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
    }

    .btn-icon svg {
      width: 18px;
      height: 18px;
    }

    .btn-spinner {
      width: 18px;
      height: 18px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
  }
}

// 蒸馏结果
.distill-results {
  margin: 0 12px 12px;
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e8ecf1;

  .results-title {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    font-size: 14px;
    font-weight: 500;
    color: #1a1f36;

    svg {
      color: #10b981;
    }

    .results-count {
      font-weight: normal;
      color: #9ca3af;
    }
  }

  .save-all-btn {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    background: #4a90e2;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    color: white;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: #357abd;
    }
  }
}

.results-list {
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

// 结果项
.result-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 10px;
  margin-bottom: 8px;
  border-left: 3px solid transparent;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
  }

  &.saved {
    border-left-color: #10b981;
    background: linear-gradient(90deg, rgba(16, 185, 129, 0.05) 0%, transparent 100%);
  }

  .result-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .result-content {
    flex: 1;
    min-width: 0;

    .result-keyword {
      margin-bottom: 8px;

      .keyword-tag {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.08) 100%);
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        color: #d97706;
      }
    }

    .result-questions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;

      .question-chip {
        padding: 4px 10px;
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        font-size: 12px;
        color: #6b7280;
      }
    }
  }

  .result-action {
    flex-shrink: 0;

    .action-btn {
      padding: 6px 12px;
      background: #4a90e2;
      border: none;
      border-radius: 6px;
      font-size: 12px;
      color: white;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: #357abd;
      }
    }

    .saved-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      background: #d1fae5;
      border-radius: 6px;
      font-size: 11px;
      color: #059669;
      font-weight: 500;
    }
  }
}

// 骨架屏
.result-skeleton {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 10px;
  margin-bottom: 8px;

  .skeleton-number {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    flex-shrink: 0;
  }

  .skeleton-content {
    flex: 1;

    .skeleton-keyword {
      width: 80px;
      height: 28px;
      border-radius: 6px;
      background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      margin-bottom: 8px;
    }

    .skeleton-questions {
      display: flex;
      gap: 6px;

      .skeleton-question {
        width: 120px;
        height: 24px;
        border-radius: 6px;
        background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
      }
    }
  }
}

// 滚动条样式
.results-list::-webkit-scrollbar {
  width: 4px;
}

.results-list::-webkit-scrollbar-track {
  background: transparent;
}

.results-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 2px;
}

// 动画
@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

// 列表过渡动画
.result-enter-active {
  transition: all 0.3s ease;
}

.result-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

.result-enter-to {
  opacity: 1;
  transform: translateX(0);
}
</style>
